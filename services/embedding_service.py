"""
Embedding Service for OpenAI Integration

Handles generation of vector embeddings using OpenAI's embedding models.
Includes batch processing, rate limiting, and error handling.

Example:
    >>> from services.embedding_service import EmbeddingService
    >>> service = EmbeddingService()
    >>> embeddings = await service.generate_embeddings(
    ...     texts=["Hello world", "Test text"],
    ...     correlation_id="trace-123"
    ... )
"""

import logging
from typing import List, Dict, Any, Optional
import asyncio

from config import settings

logger = logging.getLogger(__name__)


class EmbeddingError(Exception):
    """Exception raised when embedding generation fails.

    Example:
        >>> raise EmbeddingError("Rate limit exceeded", retry_after=60)
    """

    def __init__(self, message: str, **context):
        self.message = message
        self.context = context
        super().__init__(message)


class EmbeddingService:
    """Service for generating vector embeddings using OpenAI.

    Handles batch processing, rate limiting, and retries for embedding generation.

    Attributes:
        model: OpenAI embedding model name
        batch_size: Number of texts to embed per API call
        max_retries: Maximum retry attempts

    Example:
        >>> service = EmbeddingService(
        ...     model="text-embedding-3-small",
        ...     batch_size=100
        ... )
        >>> vectors = await service.generate_embeddings(["text1", "text2"])
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        batch_size: Optional[int] = None,
        max_retries: int = 3
    ):
        """Initialize embedding service.

        Args:
            api_key: OpenAI API key (defaults to settings)
            model: Embedding model name (defaults to settings)
            batch_size: Batch size for API calls (defaults to settings)
            max_retries: Maximum retry attempts

        Example:
            >>> service = EmbeddingService(
            ...     model="text-embedding-3-small",
            ...     batch_size=50
            ... )
        """
        self.api_key = api_key or settings.OPENAI_API_KEY
        self.model = model or settings.OPENAI_EMBEDDING_MODEL
        self.batch_size = batch_size or settings.OPENAI_BATCH_SIZE
        self.max_retries = max_retries
        self.logger = logging.getLogger(__name__)

        # Validate API key
        if not self.api_key:
            raise ValueError("OpenAI API key is required")

        # Initialize OpenAI client
        self._client: Optional[Any] = None

    def _get_client(self):
        """Get or create OpenAI client.

        Returns:
            OpenAI client instance

        Example:
            >>> client = service._get_client()
        """
        if self._client is None:
            try:
                from openai import AsyncOpenAI
            except ImportError:
                raise EmbeddingError(
                    "openai package not installed. Install with: pip install openai"
                )

            self._client = AsyncOpenAI(api_key=self.api_key)

        return self._client

    async def generate_embeddings(
        self,
        texts: List[str],
        correlation_id: str,
        model: Optional[str] = None
    ) -> List[List[float]]:
        """Generate embeddings for a list of texts.

        Automatically batches requests to stay within API limits.

        Args:
            texts: List of text strings to embed
            correlation_id: Distributed tracing ID
            model: Optional model override

        Returns:
            List of embedding vectors (one per text)

        Raises:
            EmbeddingError: If embedding generation fails

        Example:
            >>> embeddings = await service.generate_embeddings(
            ...     texts=["Hello world", "Test text"],
            ...     correlation_id="trace-123"
            ... )
            >>> print(len(embeddings))  # 2
            >>> print(len(embeddings[0]))  # 1536
        """
        if not texts:
            return []

        model = model or self.model
        client = self._get_client()

        self.logger.info(
            f"Generating embeddings for {len(texts)} texts",
            extra={
                "correlation_id": correlation_id,
                "text_count": len(texts),
                "model": model,
                "batch_size": self.batch_size
            }
        )

        all_embeddings: List[List[float]] = []

        # Process in batches
        for i in range(0, len(texts), self.batch_size):
            batch = texts[i:i + self.batch_size]
            batch_num = i // self.batch_size + 1
            total_batches = (len(texts) + self.batch_size - 1) // self.batch_size

            self.logger.debug(
                f"Processing batch {batch_num}/{total_batches} ({len(batch)} texts)",
                extra={
                    "correlation_id": correlation_id,
                    "batch_num": batch_num,
                    "batch_size": len(batch)
                }
            )

            # Generate embeddings for this batch with retry
            batch_embeddings = await self._generate_batch_with_retry(
                texts=batch,
                model=model,
                correlation_id=correlation_id
            )

            all_embeddings.extend(batch_embeddings)

            self.logger.debug(
                f"Batch {batch_num}/{total_batches} completed",
                extra={
                    "correlation_id": correlation_id,
                    "embeddings_generated": len(batch_embeddings)
                }
            )

        self.logger.info(
            f"Generated {len(all_embeddings)} embeddings",
            extra={
                "correlation_id": correlation_id,
                "total_embeddings": len(all_embeddings)
            }
        )

        return all_embeddings

    async def _generate_batch_with_retry(
        self,
        texts: List[str],
        model: str,
        correlation_id: str
    ) -> List[List[float]]:
        """Generate embeddings for a batch with retry logic.

        Args:
            texts: Batch of texts to embed
            model: Model name
            correlation_id: Distributed tracing ID

        Returns:
            List of embedding vectors

        Raises:
            EmbeddingError: If all retry attempts fail
        """
        last_error = None

        for attempt in range(1, self.max_retries + 1):
            try:
                embeddings = await self._generate_batch(texts, model, correlation_id)
                return embeddings

            except Exception as e:
                last_error = e
                self.logger.warning(
                    f"Embedding attempt {attempt}/{self.max_retries} failed: {str(e)}",
                    extra={
                        "correlation_id": correlation_id,
                        "attempt": attempt,
                        "error": str(e)
                    }
                )

                if attempt < self.max_retries:
                    # Exponential backoff
                    backoff = 2 ** attempt
                    self.logger.info(
                        f"Retrying in {backoff} seconds...",
                        extra={
                            "correlation_id": correlation_id,
                            "backoff_seconds": backoff
                        }
                    )
                    await asyncio.sleep(backoff)

        # All retries failed
        error_msg = f"Failed to generate embeddings after {self.max_retries} attempts: {str(last_error)}"
        self.logger.error(
            error_msg,
            extra={
                "correlation_id": correlation_id,
                "max_retries": self.max_retries
            },
            exc_info=True
        )
        raise EmbeddingError(error_msg, original_error=str(last_error))

    async def _generate_batch(
        self,
        texts: List[str],
        model: str,
        correlation_id: str
    ) -> List[List[float]]:
        """Generate embeddings for a single batch.

        Args:
            texts: Batch of texts to embed
            model: Model name
            correlation_id: Distributed tracing ID

        Returns:
            List of embedding vectors

        Raises:
            Exception: If API call fails
        """
        client = self._get_client()

        try:
            response = await client.embeddings.create(
                input=texts,
                model=model
            )

            # Extract embeddings from response
            embeddings = [item.embedding for item in response.data]

            return embeddings

        except Exception as e:
            self.logger.error(
                f"OpenAI API error: {str(e)}",
                extra={
                    "correlation_id": correlation_id,
                    "model": model,
                    "batch_size": len(texts),
                    "error": str(e)
                },
                exc_info=True
            )
            raise

    async def get_embedding_dimension(self, model: Optional[str] = None) -> int:
        """Get the embedding dimension for a model.

        Args:
            model: Model name (defaults to self.model)

        Returns:
            Embedding dimension

        Example:
            >>> dim = await service.get_embedding_dimension()
            >>> print(dim)  # 1536
        """
        model = model or self.model

        # Known dimensions for OpenAI models
        dimensions = {
            "text-embedding-3-small": 1536,
            "text-embedding-3-large": 3072,
            "text-embedding-ada-002": 1536
        }

        return dimensions.get(model, 1536)  # Default to 1536

    async def close(self) -> None:
        """Close the OpenAI client.

        Should be called during application shutdown.

        Example:
            >>> await service.close()
        """
        if self._client:
            await self._client.close()
            self._client = None


# Example usage
if __name__ == "__main__":
    import asyncio
    from uuid import uuid4

    async def test_embedding_service():
        """Test the embedding service."""
        # Note: Requires valid OPENAI_API_KEY in environment
        service = EmbeddingService(batch_size=2)
        correlation_id = str(uuid4())

        texts = [
            "This is the first test document.",
            "This is the second test document.",
            "And here is a third test document."
        ]

        try:
            # Generate embeddings
            embeddings = await service.generate_embeddings(
                texts=texts,
                correlation_id=correlation_id
            )

            print(f"Generated {len(embeddings)} embeddings")
            print(f"Embedding dimension: {len(embeddings[0])}")
            print(f"First embedding preview: {embeddings[0][:5]}...")

            # Get dimension
            dim = await service.get_embedding_dimension()
            print(f"Model dimension: {dim}")

        except Exception as e:
            print(f"Error: {str(e)}")

        finally:
            await service.close()

    # Uncomment to test (requires valid API key)
    # asyncio.run(test_embedding_service())
    print("EmbeddingService defined. Set OPENAI_API_KEY and run test to verify.")
