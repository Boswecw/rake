"""
Pipeline Stage 5: STORE

Stores embeddings and metadata in DataForge.
This is the fifth and final stage of the 5-stage pipeline.

Example:
    >>> from pipeline.store import StoreStage
    >>> stage = StoreStage()
    >>> stored_docs = await stage.execute(
    ...     embeddings=embeddings,
    ...     correlation_id="trace-123"
    ... )
"""

import logging
import time
from typing import List, Dict, Any, Optional
from uuid import uuid4
from datetime import datetime

from models.document import Embedding, StoredDocument, DocumentSource, ProcessingStatus
from services.dataforge_client import DataForgeClient, DataForgeError
from services.telemetry_db_client import telemetry

logger = logging.getLogger(__name__)


class StoreStageError(Exception):
    """Exception raised when store stage fails.

    Example:
        >>> raise StoreStageError("Storage failed", document_id="doc-123")
    """

    def __init__(self, message: str, **context):
        self.message = message
        self.context = context
        super().__init__(message)


class StoreStage:
    """Stage 5: Store embeddings and metadata in DataForge.

    Persists embeddings and document metadata to DataForge's PostgreSQL
    database with pgvector for semantic search.

    Attributes:
        dataforge_client: DataForgeClient instance

    Example:
        >>> stage = StoreStage()
        >>> stored_docs = await stage.execute(embeddings, "trace-123")
    """

    def __init__(
        self,
        dataforge_client: Optional[DataForgeClient] = None
    ):
        """Initialize store stage.

        Args:
            dataforge_client: DataForgeClient instance (creates new if None)

        Example:
            >>> client = DataForgeClient(timeout=60)
            >>> stage = StoreStage(dataforge_client=client)
        """
        self.dataforge_client = dataforge_client or DataForgeClient()
        self.logger = logging.getLogger(__name__)

    def _group_embeddings_by_document(
        self,
        embeddings: List[Embedding]
    ) -> Dict[str, List[Embedding]]:
        """Group embeddings by their parent document ID.

        Args:
            embeddings: List of embeddings

        Returns:
            Dict mapping document_id to list of embeddings

        Example:
            >>> grouped = stage._group_embeddings_by_document(embeddings)
            >>> print(grouped.keys())
            dict_keys(['doc-1', 'doc-2'])
        """
        grouped: Dict[str, List[Embedding]] = {}

        for embedding in embeddings:
            # Get document_id from embedding metadata
            doc_id = embedding.metadata.get("document_id", "unknown")

            if doc_id not in grouped:
                grouped[doc_id] = []

            grouped[doc_id].append(embedding)

        return grouped

    def _create_stored_document(
        self,
        document_id: str,
        embeddings: List[Embedding],
        source: str = "unknown",
        url: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        tenant_id: Optional[str] = None
    ) -> StoredDocument:
        """Create a StoredDocument from embeddings.

        Args:
            document_id: Document identifier
            embeddings: List of embeddings for this document
            source: Document source type
            url: Optional source URL
            metadata: Document metadata
            tenant_id: Multi-tenant identifier

        Returns:
            StoredDocument instance

        Example:
            >>> doc = stage._create_stored_document(
            ...     document_id="doc-1",
            ...     embeddings=embeddings,
            ...     source="file_upload"
            ... )
        """
        # Extract unique chunk IDs
        chunk_ids = list(set(e.chunk_id for e in embeddings))

        return StoredDocument(
            id=document_id,
            source=DocumentSource(source) if source in [s.value for s in DocumentSource] else DocumentSource.FILE_UPLOAD,
            url=url,
            metadata=metadata or embeddings[0].metadata if embeddings else {},
            chunk_count=len(chunk_ids),
            embedding_count=len(embeddings),
            status=ProcessingStatus.COMPLETED,
            tenant_id=tenant_id or (embeddings[0].tenant_id if embeddings else None)
        )

    async def execute(
        self,
        embeddings: List[Embedding],
        correlation_id: str,
        job_id: Optional[str] = None,
        tenant_id: Optional[str] = None,
        source: str = "unknown",
        url: Optional[str] = None
    ) -> List[StoredDocument]:
        """Execute the store stage.

        Stores all embeddings and document metadata in DataForge.

        Args:
            embeddings: List of embeddings to store
            correlation_id: Distributed tracing ID
            job_id: Optional job identifier
            tenant_id: Multi-tenant identifier
            source: Document source type
            url: Optional source URL

        Returns:
            List of StoredDocument objects

        Raises:
            StoreStageError: If storage fails

        Example:
            >>> stored_docs = await stage.execute(
            ...     embeddings=embeddings,
            ...     correlation_id="trace-123",
            ...     job_id="job-456",
            ...     tenant_id="tenant-789",
            ...     source="file_upload"
            ... )
            >>> print(f"Stored {len(stored_docs)} documents")
        """
        start_time = time.time()
        job_id = job_id or f"job-{uuid4().hex[:12]}"

        if not embeddings:
            self.logger.warning(
                "No embeddings provided for storage",
                extra={
                    "correlation_id": correlation_id,
                    "job_id": job_id
                }
            )
            return []

        self.logger.info(
            f"Starting store stage for {len(embeddings)} embeddings",
            extra={
                "correlation_id": correlation_id,
                "job_id": job_id,
                "embedding_count": len(embeddings),
                "tenant_id": tenant_id
            }
        )

        try:
            # Store embeddings in DataForge
            self.logger.debug(
                f"Storing {len(embeddings)} embeddings in DataForge",
                extra={
                    "correlation_id": correlation_id,
                    "embedding_count": len(embeddings)
                }
            )

            store_result = await self.dataforge_client.store_embeddings(
                embeddings=embeddings,
                correlation_id=correlation_id,
                tenant_id=tenant_id
            )

            self.logger.info(
                f"Stored embeddings: {store_result}",
                extra={
                    "correlation_id": correlation_id,
                    "store_result": store_result
                }
            )

            # Group embeddings by document to create StoredDocument records
            grouped = self._group_embeddings_by_document(embeddings)

            self.logger.debug(
                f"Grouped embeddings into {len(grouped)} documents",
                extra={
                    "correlation_id": correlation_id,
                    "document_count": len(grouped)
                }
            )

            # Create and store document metadata
            stored_documents: List[StoredDocument] = []

            for doc_id, doc_embeddings in grouped.items():
                # Create StoredDocument
                stored_doc = self._create_stored_document(
                    document_id=doc_id,
                    embeddings=doc_embeddings,
                    source=source,
                    url=url,
                    tenant_id=tenant_id
                )

                # Store document metadata
                await self.dataforge_client.store_document_metadata(
                    document=stored_doc,
                    correlation_id=correlation_id
                )

                stored_documents.append(stored_doc)

                self.logger.debug(
                    f"Stored document metadata: {doc_id}",
                    extra={
                        "correlation_id": correlation_id,
                        "document_id": doc_id,
                        "chunk_count": stored_doc.chunk_count,
                        "embedding_count": stored_doc.embedding_count
                    }
                )

            # Calculate duration
            duration_ms = (time.time() - start_time) * 1000

            # Calculate statistics
            total_chunks = sum(doc.chunk_count for doc in stored_documents)
            total_embeddings = sum(doc.embedding_count for doc in stored_documents)

            # Emit telemetry
            await telemetry.emit_phase_completed(
                job_id=job_id,
                phase="store",
                phase_number=5,
                correlation_id=correlation_id,
                duration_ms=duration_ms,
                items_processed=len(stored_documents),
                tenant_id=tenant_id,
                metadata={
                    "document_count": len(stored_documents),
                    "total_chunks": total_chunks,
                    "total_embeddings": total_embeddings,
                    "store_result": store_result
                }
            )

            self.logger.info(
                f"Store stage completed: {len(stored_documents)} documents in {duration_ms:.2f}ms",
                extra={
                    "correlation_id": correlation_id,
                    "job_id": job_id,
                    "document_count": len(stored_documents),
                    "total_embeddings": total_embeddings,
                    "duration_ms": duration_ms
                }
            )

            return stored_documents

        except DataForgeError as e:
            duration_ms = (time.time() - start_time) * 1000

            self.logger.error(
                f"Store stage failed: {str(e)}",
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
                source=source,
                correlation_id=correlation_id,
                failed_stage="store",
                error_type=e.__class__.__name__,
                error_message=str(e),
                tenant_id=tenant_id
            )

            raise StoreStageError(
                f"Storage failed: {str(e)}",
                error=str(e),
                **e.context if hasattr(e, 'context') else {}
            )

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000

            self.logger.error(
                f"Unexpected error in store stage: {str(e)}",
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
                source=source,
                correlation_id=correlation_id,
                failed_stage="store",
                error_type=e.__class__.__name__,
                error_message=str(e),
                tenant_id=tenant_id
            )

            raise StoreStageError(
                f"Unexpected error: {str(e)}",
                error=str(e)
            )

    async def close(self) -> None:
        """Close the DataForge client.

        Should be called during application shutdown.

        Example:
            >>> await stage.close()
        """
        if self.dataforge_client:
            await self.dataforge_client.close()


# Example usage
if __name__ == "__main__":
    import asyncio

    async def test_store_stage():
        """Test the store stage."""
        # Note: Requires DataForge to be running
        stage = StoreStage()
        correlation_id = str(uuid4())

        # Create test embeddings
        embeddings = [
            Embedding(
                chunk_id="chunk-1",
                vector=[0.1] * 1536,
                model="text-embedding-3-small",
                metadata={"document_id": "doc-1", "test": True},
                tenant_id="tenant-test"
            ),
            Embedding(
                chunk_id="chunk-2",
                vector=[0.2] * 1536,
                model="text-embedding-3-small",
                metadata={"document_id": "doc-1", "test": True},
                tenant_id="tenant-test"
            )
        ]

        try:
            # Execute store stage
            stored_docs = await stage.execute(
                embeddings=embeddings,
                correlation_id=correlation_id,
                job_id="job-test",
                tenant_id="tenant-test",
                source="file_upload"
            )

            print(f"Stored {len(stored_docs)} document(s)\n")

            for doc in stored_docs:
                print(f"Document ID: {doc.id}")
                print(f"Source: {doc.source}")
                print(f"Chunks: {doc.chunk_count}")
                print(f"Embeddings: {doc.embedding_count}")
                print(f"Status: {doc.status}")
                print()

        except Exception as e:
            print(f"Error: {str(e)}")

        finally:
            await stage.close()
            await telemetry.close()

    # Uncomment to test (requires DataForge running)
    # asyncio.run(test_store_stage())
    print("StoreStage defined. Run DataForge and uncomment test to verify.")
