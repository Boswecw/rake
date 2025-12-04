"""
Pipeline Stage 4: EMBED

Generates vector embeddings for chunks using OpenAI.
This is the fourth stage of the 5-stage pipeline.

Example:
    >>> from pipeline.embed import EmbedStage
    >>> stage = EmbedStage()
    >>> embeddings = await stage.execute(
    ...     chunks=chunks,
    ...     correlation_id="trace-123"
    ... )
"""

import logging
import time
from typing import List, Optional
from uuid import uuid4

from models.document import Chunk, Embedding
from services.embedding_service import EmbeddingService, EmbeddingError
from services.telemetry_client import telemetry

logger = logging.getLogger(__name__)


class EmbedStageError(Exception):
    """Exception raised when embed stage fails.

    Example:
        >>> raise EmbedStageError("Embedding failed", chunk_id="chunk-123")
    """

    def __init__(self, message: str, **context):
        self.message = message
        self.context = context
        super().__init__(message)


class EmbedStage:
    """Stage 4: Generate vector embeddings for chunks.

    Uses OpenAI's embedding API to generate vector representations
    of text chunks for semantic search.

    Attributes:
        embedding_service: EmbeddingService instance
        model: Embedding model name

    Example:
        >>> stage = EmbedStage(model="text-embedding-3-small")
        >>> embeddings = await stage.execute(chunks, "trace-123")
    """

    def __init__(
        self,
        embedding_service: Optional[EmbeddingService] = None,
        model: Optional[str] = None
    ):
        """Initialize embed stage.

        Args:
            embedding_service: EmbeddingService instance (creates new if None)
            model: Embedding model name

        Example:
            >>> service = EmbeddingService(batch_size=50)
            >>> stage = EmbedStage(embedding_service=service)
        """
        self.embedding_service = embedding_service or EmbeddingService(model=model)
        self.model = model
        self.logger = logging.getLogger(__name__)

    async def execute(
        self,
        chunks: List[Chunk],
        correlation_id: str,
        job_id: Optional[str] = None,
        tenant_id: Optional[str] = None
    ) -> List[Embedding]:
        """Execute the embed stage.

        Generates embeddings for all chunks and emits telemetry.

        Args:
            chunks: List of chunks to embed
            correlation_id: Distributed tracing ID
            job_id: Optional job identifier
            tenant_id: Multi-tenant identifier

        Returns:
            List of Embedding objects

        Raises:
            EmbedStageError: If embedding generation fails

        Example:
            >>> embeddings = await stage.execute(
            ...     chunks=chunks,
            ...     correlation_id="trace-123",
            ...     job_id="job-456"
            ... )
            >>> print(f"Generated {len(embeddings)} embeddings")
        """
        start_time = time.time()
        job_id = job_id or f"job-{uuid4().hex[:12]}"

        if not chunks:
            self.logger.warning(
                "No chunks provided for embedding",
                extra={
                    "correlation_id": correlation_id,
                    "job_id": job_id
                }
            )
            return []

        self.logger.info(
            f"Starting embed stage for {len(chunks)} chunks",
            extra={
                "correlation_id": correlation_id,
                "job_id": job_id,
                "chunk_count": len(chunks),
                "tenant_id": tenant_id
            }
        )

        try:
            # Extract text content from chunks
            texts = [chunk.content for chunk in chunks]

            self.logger.debug(
                f"Generating embeddings for {len(texts)} texts",
                extra={
                    "correlation_id": correlation_id,
                    "text_count": len(texts),
                    "avg_length": sum(len(t) for t in texts) // len(texts) if texts else 0
                }
            )

            # Generate embeddings using the service
            vectors = await self.embedding_service.generate_embeddings(
                texts=texts,
                correlation_id=correlation_id,
                model=self.model
            )

            # Create Embedding objects
            embeddings: List[Embedding] = []
            for chunk, vector in zip(chunks, vectors):
                embedding = Embedding(
                    chunk_id=chunk.id,
                    vector=vector,
                    model=self.embedding_service.model,
                    metadata={
                        **chunk.metadata,
                        "document_id": chunk.document_id,
                        "chunk_position": chunk.position,
                        "embedding_dimension": len(vector)
                    },
                    tenant_id=tenant_id or chunk.tenant_id
                )
                embeddings.append(embedding)

                self.logger.debug(
                    f"Created embedding for chunk {chunk.id}",
                    extra={
                        "correlation_id": correlation_id,
                        "chunk_id": chunk.id,
                        "embedding_id": embedding.id,
                        "vector_dimension": len(vector)
                    }
                )

            # Calculate duration
            duration_ms = (time.time() - start_time) * 1000

            # Calculate statistics
            total_tokens = sum(chunk.token_count for chunk in chunks)
            avg_vector_dim = sum(len(e.vector) for e in embeddings) / len(embeddings) if embeddings else 0

            # Emit telemetry
            await telemetry.emit_phase_completed(
                job_id=job_id,
                phase="embed",
                phase_number=4,
                correlation_id=correlation_id,
                duration_ms=duration_ms,
                items_processed=len(embeddings),
                tenant_id=tenant_id,
                metadata={
                    "chunk_count": len(chunks),
                    "embedding_count": len(embeddings),
                    "total_tokens": total_tokens,
                    "model": self.embedding_service.model,
                    "vector_dimension": int(avg_vector_dim)
                }
            )

            self.logger.info(
                f"Embed stage completed: {len(embeddings)} embeddings in {duration_ms:.2f}ms",
                extra={
                    "correlation_id": correlation_id,
                    "job_id": job_id,
                    "embedding_count": len(embeddings),
                    "total_tokens": total_tokens,
                    "duration_ms": duration_ms
                }
            )

            return embeddings

        except EmbeddingError as e:
            duration_ms = (time.time() - start_time) * 1000

            self.logger.error(
                f"Embed stage failed: {str(e)}",
                extra={
                    "correlation_id": correlation_id,
                    "job_id": job_id,
                    "error": str(e),
                    "duration_ms": duration_ms
                },
                exc_info=True
            )

            # Emit failure telemetry
            await telemetry.emit_job_failed(
                job_id=job_id,
                source="unknown",
                correlation_id=correlation_id,
                failed_stage="embed",
                error_type=e.__class__.__name__,
                error_message=str(e),
                tenant_id=tenant_id
            )

            raise EmbedStageError(
                f"Embedding failed: {str(e)}",
                error=str(e),
                **e.context if hasattr(e, 'context') else {}
            )

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000

            self.logger.error(
                f"Unexpected error in embed stage: {str(e)}",
                extra={
                    "correlation_id": correlation_id,
                    "job_id": job_id,
                    "error": str(e),
                    "duration_ms": duration_ms
                },
                exc_info=True
            )

            # Emit failure telemetry
            await telemetry.emit_job_failed(
                job_id=job_id,
                source="unknown",
                correlation_id=correlation_id,
                failed_stage="embed",
                error_type=e.__class__.__name__,
                error_message=str(e),
                tenant_id=tenant_id
            )

            raise EmbedStageError(
                f"Unexpected error: {str(e)}",
                error=str(e)
            )

    async def close(self) -> None:
        """Close the embedding service.

        Should be called during application shutdown.

        Example:
            >>> await stage.close()
        """
        if self.embedding_service:
            await self.embedding_service.close()


# Example usage
if __name__ == "__main__":
    import asyncio

    async def test_embed_stage():
        """Test the embed stage."""
        # Note: Requires valid OPENAI_API_KEY in environment
        stage = EmbedStage()
        correlation_id = str(uuid4())

        # Create test chunks
        chunks = [
            Chunk(
                id="chunk-1",
                document_id="doc-1",
                content="This is the first test chunk with some content.",
                position=0,
                token_count=10,
                start_char=0,
                end_char=48,
                metadata={"test": True}
            ),
            Chunk(
                id="chunk-2",
                document_id="doc-1",
                content="This is the second test chunk with different content.",
                position=1,
                token_count=11,
                start_char=48,
                end_char=102,
                metadata={"test": True}
            )
        ]

        try:
            # Execute embed stage
            embeddings = await stage.execute(
                chunks=chunks,
                correlation_id=correlation_id,
                job_id="job-test",
                tenant_id="tenant-test"
            )

            print(f"Generated {len(embeddings)} embeddings\n")

            for embedding in embeddings:
                print(f"Embedding ID: {embedding.id}")
                print(f"Chunk ID: {embedding.chunk_id}")
                print(f"Model: {embedding.model}")
                print(f"Vector dimension: {len(embedding.vector)}")
                print(f"Vector preview: {embedding.vector[:5]}...")
                print()

        except Exception as e:
            print(f"Error: {str(e)}")

        finally:
            await stage.close()
            await telemetry.close()

    # Uncomment to test (requires valid API key)
    # asyncio.run(test_embed_stage())
    print("EmbedStage defined. Set OPENAI_API_KEY and run test to verify.")
