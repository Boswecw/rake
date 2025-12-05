"""
Pipeline Orchestrator

Coordinates the complete 5-stage data ingestion pipeline:
    1. FETCH  → Retrieve documents
    2. CLEAN  → Normalize text
    3. CHUNK  → Split into segments
    4. EMBED  → Generate vectors
    5. STORE  → Persist to DataForge

Example:
    >>> from pipeline.orchestrator import PipelineOrchestrator
    >>> orchestrator = PipelineOrchestrator()
    >>> result = await orchestrator.run(
    ...     source="file_upload",
    ...     file_path="/path/to/doc.pdf",
    ...     tenant_id="tenant-123"
    ... )
"""

import logging
import time
from typing import Dict, Any, Optional
from uuid import uuid4
from datetime import datetime

from models.document import PipelineJob, ProcessingStatus, DocumentSource
from pipeline.fetch import FetchStage, FetchStageError
from pipeline.clean import CleanStage, CleanStageError
from pipeline.chunk import ChunkStage, ChunkStageError
from pipeline.embed import EmbedStage, EmbedStageError
from pipeline.store import StoreStage, StoreStageError
from services.telemetry_db_client import telemetry

logger = logging.getLogger(__name__)


class PipelineError(Exception):
    """Exception raised when pipeline execution fails.

    Example:
        >>> raise PipelineError("Pipeline failed at clean stage", stage="clean")
    """

    def __init__(self, message: str, **context):
        self.message = message
        self.context = context
        super().__init__(message)


class PipelineOrchestrator:
    """Orchestrates the complete 5-stage pipeline.

    Manages execution of all pipeline stages in sequence, with error
    handling, telemetry emission, and job tracking.

    Attributes:
        fetch_stage: Stage 1 - Fetch documents
        clean_stage: Stage 2 - Clean text
        chunk_stage: Stage 3 - Create chunks
        embed_stage: Stage 4 - Generate embeddings
        store_stage: Stage 5 - Store in DataForge

    Example:
        >>> orchestrator = PipelineOrchestrator()
        >>> result = await orchestrator.run(
        ...     source="file_upload",
        ...     file_path="document.pdf",
        ...     tenant_id="tenant-123"
        ... )
    """

    def __init__(
        self,
        fetch_stage: Optional[FetchStage] = None,
        clean_stage: Optional[CleanStage] = None,
        chunk_stage: Optional[ChunkStage] = None,
        embed_stage: Optional[EmbedStage] = None,
        store_stage: Optional[StoreStage] = None
    ):
        """Initialize pipeline orchestrator.

        Args:
            fetch_stage: Custom FetchStage (creates default if None)
            clean_stage: Custom CleanStage (creates default if None)
            chunk_stage: Custom ChunkStage (creates default if None)
            embed_stage: Custom EmbedStage (creates default if None)
            store_stage: Custom StoreStage (creates default if None)

        Example:
            >>> orchestrator = PipelineOrchestrator(
            ...     chunk_stage=ChunkStage(chunk_size=1000),
            ...     embed_stage=EmbedStage(model="text-embedding-3-large")
            ... )
        """
        self.fetch_stage = fetch_stage or FetchStage()
        self.clean_stage = clean_stage or CleanStage()
        self.chunk_stage = chunk_stage or ChunkStage()
        self.embed_stage = embed_stage or EmbedStage()
        self.store_stage = store_stage or StoreStage()
        self.logger = logging.getLogger(__name__)

    async def run(
        self,
        source: str,
        tenant_id: Optional[str] = None,
        job_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
        **source_params
    ) -> Dict[str, Any]:
        """Run the complete 5-stage pipeline.

        Executes all stages in sequence, emitting telemetry at each step.

        Args:
            source: Source type (file_upload, url_scrape, etc.)
            tenant_id: Multi-tenant identifier
            job_id: Optional job identifier (auto-generated if None)
            correlation_id: Optional correlation ID (auto-generated if None)
            **source_params: Source-specific parameters (file_path, url, etc.)

        Returns:
            Dict with pipeline results:
                - job_id: Job identifier
                - status: Pipeline status
                - documents_stored: Number of documents stored
                - chunks_created: Number of chunks created
                - embeddings_generated: Number of embeddings generated
                - duration_ms: Total duration in milliseconds
                - stages_completed: List of completed stage names

        Raises:
            PipelineError: If any stage fails

        Example:
            >>> result = await orchestrator.run(
            ...     source="file_upload",
            ...     tenant_id="tenant-123",
            ...     file_path="/path/to/document.pdf"
            ... )
            >>> print(f"Job {result['job_id']}: {result['status']}")
            >>> print(f"Created {result['chunks_created']} chunks")
        """
        # Generate IDs
        job_id = job_id or f"job-{uuid4().hex[:12]}"
        correlation_id = correlation_id or str(uuid4())

        # Track pipeline execution
        start_time = time.time()
        job = PipelineJob(
            job_id=job_id,
            document_id="",  # Will be set after fetch
            source=DocumentSource(source),
            status=ProcessingStatus.PENDING,
            current_stage=0,
            tenant_id=tenant_id,
            correlation_id=correlation_id
        )

        self.logger.info(
            f"Starting pipeline job: {job_id}",
            extra={
                "correlation_id": correlation_id,
                "job_id": job_id,
                "source": source,
                "tenant_id": tenant_id
            }
        )

        # Emit job started event
        await telemetry.emit_job_started(
            job_id=job_id,
            source=source,
            correlation_id=correlation_id,
            scheduled=source_params.get("scheduled", False),
            tenant_id=tenant_id
        )

        try:
            # ============================================================
            # STAGE 1: FETCH
            # ============================================================
            job.status = ProcessingStatus.FETCHING
            job.current_stage = 1

            raw_documents = await self.fetch_stage.execute(
                source=source,
                correlation_id=correlation_id,
                job_id=job_id,
                tenant_id=tenant_id,
                **source_params
            )

            job.stages_completed.append("fetch")
            job.document_id = raw_documents[0].id if raw_documents else "unknown"

            self.logger.info(
                f"Stage 1/5 complete: Fetched {len(raw_documents)} documents",
                extra={
                    "correlation_id": correlation_id,
                    "job_id": job_id,
                    "document_count": len(raw_documents)
                }
            )

            # ============================================================
            # STAGE 2: CLEAN
            # ============================================================
            job.status = ProcessingStatus.CLEANING
            job.current_stage = 2

            cleaned_documents = await self.clean_stage.execute(
                documents=raw_documents,
                correlation_id=correlation_id,
                job_id=job_id,
                tenant_id=tenant_id
            )

            job.stages_completed.append("clean")

            self.logger.info(
                f"Stage 2/5 complete: Cleaned {len(cleaned_documents)} documents",
                extra={
                    "correlation_id": correlation_id,
                    "job_id": job_id,
                    "document_count": len(cleaned_documents),
                    "total_words": sum(d.word_count for d in cleaned_documents)
                }
            )

            # ============================================================
            # STAGE 3: CHUNK
            # ============================================================
            job.status = ProcessingStatus.CHUNKING
            job.current_stage = 3

            chunks = await self.chunk_stage.execute(
                documents=cleaned_documents,
                correlation_id=correlation_id,
                job_id=job_id,
                tenant_id=tenant_id
            )

            job.stages_completed.append("chunk")

            self.logger.info(
                f"Stage 3/5 complete: Created {len(chunks)} chunks",
                extra={
                    "correlation_id": correlation_id,
                    "job_id": job_id,
                    "chunk_count": len(chunks),
                    "avg_chunk_size": sum(c.token_count for c in chunks) / len(chunks) if chunks else 0
                }
            )

            # ============================================================
            # STAGE 4: EMBED
            # ============================================================
            job.status = ProcessingStatus.EMBEDDING
            job.current_stage = 4

            embeddings = await self.embed_stage.execute(
                chunks=chunks,
                correlation_id=correlation_id,
                job_id=job_id,
                tenant_id=tenant_id
            )

            job.stages_completed.append("embed")

            self.logger.info(
                f"Stage 4/5 complete: Generated {len(embeddings)} embeddings",
                extra={
                    "correlation_id": correlation_id,
                    "job_id": job_id,
                    "embedding_count": len(embeddings)
                }
            )

            # ============================================================
            # STAGE 5: STORE
            # ============================================================
            job.status = ProcessingStatus.STORING
            job.current_stage = 5

            stored_documents = await self.store_stage.execute(
                embeddings=embeddings,
                correlation_id=correlation_id,
                job_id=job_id,
                tenant_id=tenant_id,
                source=source,
                url=source_params.get("file_path") or source_params.get("url")
            )

            job.stages_completed.append("store")

            self.logger.info(
                f"Stage 5/5 complete: Stored {len(stored_documents)} documents",
                extra={
                    "correlation_id": correlation_id,
                    "job_id": job_id,
                    "document_count": len(stored_documents)
                }
            )

            # ============================================================
            # PIPELINE COMPLETE
            # ============================================================
            job.status = ProcessingStatus.COMPLETED
            job.completed_at = datetime.utcnow()

            total_duration_ms = (time.time() - start_time) * 1000

            # Emit job completed event
            await telemetry.emit_job_completed(
                job_id=job_id,
                source=source,
                correlation_id=correlation_id,
                total_duration_ms=total_duration_ms,
                chunks_created=len(chunks),
                embeddings_generated=len(embeddings),
                tenant_id=tenant_id,
                metadata={
                    "documents_fetched": len(raw_documents),
                    "documents_cleaned": len(cleaned_documents),
                    "documents_stored": len(stored_documents),
                    "stages_completed": job.stages_completed
                }
            )

            self.logger.info(
                f"Pipeline completed successfully: {job_id} in {total_duration_ms:.2f}ms",
                extra={
                    "correlation_id": correlation_id,
                    "job_id": job_id,
                    "duration_ms": total_duration_ms,
                    "chunks_created": len(chunks),
                    "embeddings_generated": len(embeddings)
                }
            )

            # Return results
            return {
                "job_id": job_id,
                "correlation_id": correlation_id,
                "status": job.status.value,
                "documents_stored": len(stored_documents),
                "chunks_created": len(chunks),
                "embeddings_generated": len(embeddings),
                "duration_ms": total_duration_ms,
                "duration_seconds": total_duration_ms / 1000,
                "stages_completed": job.stages_completed,
                "tenant_id": tenant_id
            }

        except (FetchStageError, CleanStageError, ChunkStageError, EmbedStageError, StoreStageError) as e:
            # Stage-specific error already logged and telemetry emitted
            job.status = ProcessingStatus.FAILED
            job.error_message = str(e)

            total_duration_ms = (time.time() - start_time) * 1000

            self.logger.error(
                f"Pipeline failed at stage {job.current_stage}: {str(e)}",
                extra={
                    "correlation_id": correlation_id,
                    "job_id": job_id,
                    "failed_stage": job.current_stage,
                    "error": str(e),
                    "duration_ms": total_duration_ms
                },
                exc_info=True
            )

            raise PipelineError(
                f"Pipeline failed at stage {job.current_stage}: {str(e)}",
                job_id=job_id,
                failed_stage=job.current_stage,
                error=str(e)
            )

        except Exception as e:
            # Unexpected error
            job.status = ProcessingStatus.FAILED
            job.error_message = str(e)

            total_duration_ms = (time.time() - start_time) * 1000

            self.logger.error(
                f"Pipeline failed with unexpected error: {str(e)}",
                extra={
                    "correlation_id": correlation_id,
                    "job_id": job_id,
                    "current_stage": job.current_stage,
                    "error": str(e),
                    "duration_ms": total_duration_ms
                },
                exc_info=True
            )

            # Emit failure telemetry
            await telemetry.emit_job_failed(
                job_id=job_id,
                source=source,
                correlation_id=correlation_id,
                failed_stage=f"stage_{job.current_stage}",
                error_type=e.__class__.__name__,
                error_message=str(e),
                tenant_id=tenant_id
            )

            raise PipelineError(
                f"Pipeline failed: {str(e)}",
                job_id=job_id,
                current_stage=job.current_stage,
                error=str(e)
            )

    async def close(self) -> None:
        """Close all stage resources.

        Should be called during application shutdown.

        Example:
            >>> await orchestrator.close()
        """
        if self.embed_stage:
            await self.embed_stage.close()
        if self.store_stage:
            await self.store_stage.close()


# Example usage
if __name__ == "__main__":
    import asyncio
    from pathlib import Path

    async def test_pipeline():
        """Test the complete pipeline."""
        orchestrator = PipelineOrchestrator()

        # Create test file
        test_file = Path("test_pipeline.txt")
        test_file.write_text("""
        This is a comprehensive test of the Rake pipeline.

        The pipeline consists of five stages:
        1. Fetch - Retrieve documents from sources
        2. Clean - Normalize and clean text
        3. Chunk - Split into semantic segments
        4. Embed - Generate vector embeddings
        5. Store - Persist to DataForge

        Each stage is designed to be modular and testable.
        The orchestrator coordinates all stages seamlessly.
        """.strip())

        try:
            # Run pipeline
            result = await orchestrator.run(
                source="file_upload",
                tenant_id="tenant-test",
                file_path=str(test_file)
            )

            print("\n" + "="*60)
            print("PIPELINE EXECUTION COMPLETE")
            print("="*60)
            print(f"Job ID: {result['job_id']}")
            print(f"Status: {result['status']}")
            print(f"Duration: {result['duration_seconds']:.2f}s")
            print(f"Documents stored: {result['documents_stored']}")
            print(f"Chunks created: {result['chunks_created']}")
            print(f"Embeddings generated: {result['embeddings_generated']}")
            print(f"Stages completed: {', '.join(result['stages_completed'])}")
            print("="*60)

        except Exception as e:
            print(f"\nPipeline failed: {str(e)}")

        finally:
            # Cleanup
            if test_file.exists():
                test_file.unlink()
            await orchestrator.close()
            await telemetry.close()

    # Uncomment to test (requires OpenAI API key and DataForge running)
    # asyncio.run(test_pipeline())
    print("PipelineOrchestrator defined. Configure services and run test to verify.")
