"""
DataForge API Client

HTTP client for interacting with the DataForge service (port 8001).
Handles storage of documents, chunks, and embeddings with multi-tenant support.

Example:
    >>> from services.dataforge_client import DataForgeClient
    >>> client = DataForgeClient()
    >>> await client.store_embeddings(
    ...     embeddings=embeddings,
    ...     correlation_id="trace-123"
    ... )
"""

import logging
from typing import List, Dict, Any, Optional

import httpx

from config import settings
from models.document import Embedding, StoredDocument, ProcessingStatus

logger = logging.getLogger(__name__)


class DataForgeError(Exception):
    """Exception raised when DataForge API call fails.

    Example:
        >>> raise DataForgeError("API error", status_code=500)
    """

    def __init__(self, message: str, **context):
        self.message = message
        self.context = context
        super().__init__(message)


class DataForgeClient:
    """Client for DataForge API interactions.

    Handles HTTP requests to DataForge for storing documents,
    chunks, and embeddings with automatic retry and error handling.

    Attributes:
        base_url: DataForge API base URL
        timeout: Request timeout in seconds

    Example:
        >>> client = DataForgeClient(
        ...     base_url="http://localhost:8001",
        ...     timeout=30
        ... )
        >>> await client.health_check()
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        timeout: Optional[int] = None
    ):
        """Initialize DataForge client.

        Args:
            base_url: DataForge API base URL (defaults to settings)
            timeout: Request timeout in seconds (defaults to settings)

        Example:
            >>> client = DataForgeClient(
            ...     base_url="http://localhost:8001",
            ...     timeout=60
            ... )
        """
        self.base_url = base_url or settings.DATAFORGE_BASE_URL
        self.timeout = timeout or settings.DATAFORGE_TIMEOUT
        self.logger = logging.getLogger(__name__)
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create async HTTP client.

        Returns:
            Configured httpx AsyncClient

        Example:
            >>> client = await dataforge._get_client()
        """
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=self.timeout
            )
        return self._client

    async def close(self) -> None:
        """Close HTTP client.

        Should be called during application shutdown.

        Example:
            >>> await client.close()
        """
        if self._client:
            await self._client.aclose()
            self._client = None

    async def health_check(self, correlation_id: Optional[str] = None) -> bool:
        """Check if DataForge service is healthy.

        Args:
            correlation_id: Optional distributed tracing ID

        Returns:
            True if healthy, False otherwise

        Example:
            >>> is_healthy = await client.health_check()
            >>> if not is_healthy:
            ...     print("DataForge is down")
        """
        try:
            client = await self._get_client()
            response = await client.get(
                "/health",
                headers={"X-Correlation-ID": correlation_id} if correlation_id else {}
            )
            return response.status_code == 200

        except Exception as e:
            self.logger.error(
                f"DataForge health check failed: {str(e)}",
                extra={
                    "correlation_id": correlation_id,
                    "error": str(e)
                }
            )
            return False

    async def store_embeddings(
        self,
        embeddings: List[Embedding],
        correlation_id: str,
        tenant_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Store embeddings in DataForge.

        Args:
            embeddings: List of embeddings to store
            correlation_id: Distributed tracing ID
            tenant_id: Multi-tenant identifier

        Returns:
            Response data from DataForge

        Raises:
            DataForgeError: If storage fails

        Example:
            >>> result = await client.store_embeddings(
            ...     embeddings=embeddings,
            ...     correlation_id="trace-123",
            ...     tenant_id="tenant-abc"
            ... )
            >>> print(f"Stored {result['count']} embeddings")
        """
        if not embeddings:
            self.logger.warning(
                "No embeddings provided for storage",
                extra={"correlation_id": correlation_id}
            )
            return {"count": 0, "status": "no_data"}

        self.logger.info(
            f"Storing {len(embeddings)} embeddings in DataForge",
            extra={
                "correlation_id": correlation_id,
                "embedding_count": len(embeddings),
                "tenant_id": tenant_id
            }
        )

        try:
            client = await self._get_client()

            # Prepare payload
            payload = {
                "embeddings": [
                    {
                        "id": emb.id,
                        "chunk_id": emb.chunk_id,
                        "vector": emb.vector,
                        "model": emb.model,
                        "metadata": emb.metadata,
                        "created_at": emb.created_at.isoformat(),
                        "tenant_id": tenant_id or emb.tenant_id
                    }
                    for emb in embeddings
                ],
                "tenant_id": tenant_id
            }

            # Make API request
            response = await client.post(
                "/api/v1/embeddings/batch",
                json=payload,
                headers={
                    "X-Correlation-ID": correlation_id,
                    "Content-Type": "application/json"
                }
            )

            if response.status_code >= 400:
                error_msg = f"DataForge API error: HTTP {response.status_code}"
                try:
                    error_data = response.json()
                    error_msg += f" - {error_data.get('detail', 'Unknown error')}"
                except:
                    pass

                self.logger.error(
                    error_msg,
                    extra={
                        "correlation_id": correlation_id,
                        "status_code": response.status_code,
                        "response": response.text[:500]
                    }
                )
                raise DataForgeError(
                    error_msg,
                    status_code=response.status_code,
                    response=response.text[:500]
                )

            result = response.json()

            self.logger.info(
                f"Successfully stored {len(embeddings)} embeddings",
                extra={
                    "correlation_id": correlation_id,
                    "embedding_count": len(embeddings),
                    "result": result
                }
            )

            return result

        except httpx.TimeoutException:
            error_msg = f"DataForge request timed out after {self.timeout}s"
            self.logger.error(
                error_msg,
                extra={
                    "correlation_id": correlation_id,
                    "timeout": self.timeout
                }
            )
            raise DataForgeError(error_msg, timeout=self.timeout)

        except DataForgeError:
            raise  # Re-raise DataForge errors

        except Exception as e:
            error_msg = f"Failed to store embeddings: {str(e)}"
            self.logger.error(
                error_msg,
                extra={
                    "correlation_id": correlation_id,
                    "error": str(e)
                },
                exc_info=True
            )
            raise DataForgeError(error_msg, error=str(e))

    async def store_document_metadata(
        self,
        document: StoredDocument,
        correlation_id: str
    ) -> Dict[str, Any]:
        """Store document metadata in DataForge.

        Args:
            document: StoredDocument with metadata
            correlation_id: Distributed tracing ID

        Returns:
            Response data from DataForge

        Raises:
            DataForgeError: If storage fails

        Example:
            >>> result = await client.store_document_metadata(
            ...     document=stored_doc,
            ...     correlation_id="trace-123"
            ... )
        """
        self.logger.info(
            f"Storing document metadata: {document.id}",
            extra={
                "correlation_id": correlation_id,
                "document_id": document.id,
                "tenant_id": document.tenant_id
            }
        )

        try:
            client = await self._get_client()

            # Prepare payload
            payload = {
                "id": document.id,
                "source": document.source.value if hasattr(document.source, 'value') else document.source,
                "url": document.url,
                "metadata": document.metadata,
                "chunk_count": document.chunk_count,
                "embedding_count": document.embedding_count,
                "status": document.status.value if hasattr(document.status, 'value') else document.status,
                "error_message": document.error_message,
                "created_at": document.created_at.isoformat(),
                "stored_at": document.stored_at.isoformat(),
                "tenant_id": document.tenant_id
            }

            # Make API request
            response = await client.post(
                "/api/v1/documents",
                json=payload,
                headers={
                    "X-Correlation-ID": correlation_id,
                    "Content-Type": "application/json"
                }
            )

            if response.status_code >= 400:
                error_msg = f"DataForge API error: HTTP {response.status_code}"
                try:
                    error_data = response.json()
                    error_msg += f" - {error_data.get('detail', 'Unknown error')}"
                except:
                    pass

                raise DataForgeError(
                    error_msg,
                    status_code=response.status_code
                )

            result = response.json()

            self.logger.info(
                f"Successfully stored document metadata: {document.id}",
                extra={
                    "correlation_id": correlation_id,
                    "document_id": document.id
                }
            )

            return result

        except DataForgeError:
            raise

        except Exception as e:
            error_msg = f"Failed to store document metadata: {str(e)}"
            self.logger.error(
                error_msg,
                extra={
                    "correlation_id": correlation_id,
                    "document_id": document.id,
                    "error": str(e)
                },
                exc_info=True
            )
            raise DataForgeError(error_msg, error=str(e))


# Example usage
if __name__ == "__main__":
    import asyncio
    from uuid import uuid4

    async def test_dataforge_client():
        """Test the DataForge client."""
        client = DataForgeClient()
        correlation_id = str(uuid4())

        try:
            # Health check
            is_healthy = await client.health_check(correlation_id)
            print(f"DataForge healthy: {is_healthy}")

            # Note: The following would require DataForge to be running
            # and would actually store data, so it's commented out

            # # Create test embedding
            # embedding = Embedding(
            #     chunk_id="chunk-123",
            #     vector=[0.1] * 1536,  # 1536-dim vector
            #     model="text-embedding-3-small",
            #     tenant_id="tenant-test"
            # )
            #
            # # Store embedding
            # result = await client.store_embeddings(
            #     embeddings=[embedding],
            #     correlation_id=correlation_id,
            #     tenant_id="tenant-test"
            # )
            # print(f"Store result: {result}")

        finally:
            await client.close()

    asyncio.run(test_dataforge_client())
