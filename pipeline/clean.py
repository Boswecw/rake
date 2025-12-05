"""
Pipeline Stage 2: CLEAN

Normalizes and cleans text content from raw documents.
This is the second stage of the 5-stage pipeline.

Cleaning operations:
    - Remove excess whitespace
    - Normalize line endings
    - Remove special characters (optional)
    - Fix encoding issues
    - Remove duplicate content
    - Normalize unicode

Example:
    >>> from pipeline.clean import CleanStage
    >>> stage = CleanStage()
    >>> cleaned_docs = await stage.execute(
    ...     documents=raw_documents,
    ...     correlation_id="trace-123"
    ... )
"""

import logging
import re
import time
import unicodedata
from typing import List, Optional
from uuid import uuid4

from models.document import RawDocument, CleanedDocument
from services.telemetry_db_client import telemetry

logger = logging.getLogger(__name__)


class CleanStageError(Exception):
    """Exception raised when clean stage fails.

    Example:
        >>> raise CleanStageError("Cleaning failed", document_id="doc-123")
    """

    def __init__(self, message: str, **context):
        self.message = message
        self.context = context
        super().__init__(message)


class CleanStage:
    """Stage 2: Clean and normalize text content.

    Performs text normalization and cleaning operations to prepare
    documents for chunking and embedding.

    Attributes:
        remove_urls: Whether to remove URLs from text
        remove_emails: Whether to remove email addresses
        normalize_whitespace: Whether to normalize whitespace
        min_content_length: Minimum content length after cleaning

    Example:
        >>> stage = CleanStage(
        ...     remove_urls=True,
        ...     normalize_whitespace=True
        ... )
        >>> cleaned = await stage.execute(raw_docs, "trace-123")
    """

    def __init__(
        self,
        remove_urls: bool = False,
        remove_emails: bool = False,
        normalize_whitespace: bool = True,
        normalize_unicode: bool = True,
        min_content_length: int = 10
    ):
        """Initialize clean stage.

        Args:
            remove_urls: Whether to remove URLs
            remove_emails: Whether to remove email addresses
            normalize_whitespace: Whether to normalize whitespace
            normalize_unicode: Whether to normalize unicode characters
            min_content_length: Minimum content length (chars)

        Example:
            >>> stage = CleanStage(
            ...     remove_urls=True,
            ...     min_content_length=50
            ... )
        """
        self.remove_urls = remove_urls
        self.remove_emails = remove_emails
        self.normalize_whitespace = normalize_whitespace
        self.normalize_unicode = normalize_unicode
        self.min_content_length = min_content_length
        self.logger = logging.getLogger(__name__)

    def _clean_text(self, text: str) -> str:
        """Clean and normalize text content.

        Args:
            text: Raw text to clean

        Returns:
            Cleaned text

        Example:
            >>> cleaned = stage._clean_text("Hello   World\\n\\n\\nTest")
            >>> print(cleaned)
            Hello World\n\nTest
        """
        # Normalize unicode
        if self.normalize_unicode:
            text = unicodedata.normalize('NFKC', text)

        # Remove URLs
        if self.remove_urls:
            text = re.sub(
                r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+',
                '',
                text
            )

        # Remove email addresses
        if self.remove_emails:
            text = re.sub(
                r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
                '',
                text
            )

        # Normalize line endings
        text = text.replace('\r\n', '\n').replace('\r', '\n')

        # Remove excessive newlines (more than 2 consecutive)
        text = re.sub(r'\n{3,}', '\n\n', text)

        # Normalize whitespace
        if self.normalize_whitespace:
            # Replace multiple spaces with single space
            text = re.sub(r' +', ' ', text)
            # Remove spaces at start/end of lines
            text = '\n'.join(line.strip() for line in text.split('\n'))

        # Remove leading/trailing whitespace
        text = text.strip()

        return text

    def _calculate_word_count(self, text: str) -> int:
        """Calculate word count.

        Args:
            text: Text to count words in

        Returns:
            Number of words

        Example:
            >>> count = stage._calculate_word_count("Hello world test")
            >>> print(count)
            3
        """
        return len(text.split())

    async def execute(
        self,
        documents: List[RawDocument],
        correlation_id: str,
        job_id: Optional[str] = None,
        tenant_id: Optional[str] = None
    ) -> List[CleanedDocument]:
        """Execute the clean stage.

        Cleans and normalizes all documents and emits telemetry.

        Args:
            documents: List of raw documents to clean
            correlation_id: Distributed tracing ID
            job_id: Optional job identifier
            tenant_id: Multi-tenant identifier

        Returns:
            List of CleanedDocument objects

        Raises:
            CleanStageError: If cleaning fails

        Example:
            >>> cleaned_docs = await stage.execute(
            ...     documents=raw_documents,
            ...     correlation_id="trace-123",
            ...     job_id="job-456",
            ...     tenant_id="tenant-789"
            ... )
            >>> print(f"Cleaned {len(cleaned_docs)} documents")
        """
        start_time = time.time()
        job_id = job_id or f"job-{uuid4().hex[:12]}"

        self.logger.info(
            f"Starting clean stage for {len(documents)} documents",
            extra={
                "correlation_id": correlation_id,
                "job_id": job_id,
                "document_count": len(documents),
                "tenant_id": tenant_id
            }
        )

        try:
            cleaned_documents: List[CleanedDocument] = []

            for i, doc in enumerate(documents):
                self.logger.debug(
                    f"Cleaning document {i+1}/{len(documents)}: {doc.id}",
                    extra={
                        "correlation_id": correlation_id,
                        "document_id": doc.id,
                        "document_index": i+1
                    }
                )

                # Clean the content
                cleaned_content = self._clean_text(doc.content)

                # Validate minimum length
                if len(cleaned_content) < self.min_content_length:
                    self.logger.warning(
                        f"Document {doc.id} content too short after cleaning: {len(cleaned_content)} chars",
                        extra={
                            "correlation_id": correlation_id,
                            "document_id": doc.id,
                            "content_length": len(cleaned_content),
                            "min_length": self.min_content_length
                        }
                    )
                    # Skip this document or include it anyway?
                    # For now, we'll include it but log a warning
                    # Could raise an error instead if preferred

                # Calculate statistics
                word_count = self._calculate_word_count(cleaned_content)
                char_count = len(cleaned_content)

                # Create CleanedDocument
                cleaned_doc = CleanedDocument(
                    id=doc.id,
                    source=doc.source,
                    content=cleaned_content,
                    metadata={
                        **doc.metadata,
                        "original_length": len(doc.content),
                        "cleaned_length": char_count,
                        "reduction_percent": round(
                            (1 - char_count / len(doc.content)) * 100, 2
                        ) if len(doc.content) > 0 else 0
                    },
                    word_count=word_count,
                    char_count=char_count,
                    tenant_id=tenant_id or doc.tenant_id
                )

                cleaned_documents.append(cleaned_doc)

                self.logger.debug(
                    f"Cleaned document {doc.id}: {len(doc.content)} → {char_count} chars",
                    extra={
                        "correlation_id": correlation_id,
                        "document_id": doc.id,
                        "original_length": len(doc.content),
                        "cleaned_length": char_count,
                        "word_count": word_count
                    }
                )

            # Calculate duration
            duration_ms = (time.time() - start_time) * 1000

            # Calculate total statistics
            total_original = sum(len(doc.content) for doc in documents)
            total_cleaned = sum(doc.char_count for doc in cleaned_documents)
            total_words = sum(doc.word_count for doc in cleaned_documents)

            # Emit telemetry
            await telemetry.emit_phase_completed(
                job_id=job_id,
                phase="clean",
                phase_number=2,
                correlation_id=correlation_id,
                duration_ms=duration_ms,
                items_processed=len(cleaned_documents),
                tenant_id=tenant_id,
                metadata={
                    "document_count": len(cleaned_documents),
                    "total_original_chars": total_original,
                    "total_cleaned_chars": total_cleaned,
                    "total_words": total_words,
                    "avg_reduction_percent": round(
                        (1 - total_cleaned / total_original) * 100, 2
                    ) if total_original > 0 else 0
                }
            )

            self.logger.info(
                f"Clean stage completed: {len(cleaned_documents)} documents in {duration_ms:.2f}ms",
                extra={
                    "correlation_id": correlation_id,
                    "job_id": job_id,
                    "document_count": len(cleaned_documents),
                    "total_words": total_words,
                    "duration_ms": duration_ms
                }
            )

            return cleaned_documents

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000

            self.logger.error(
                f"Clean stage failed: {str(e)}",
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
                source="unknown",  # Source not available at this stage
                correlation_id=correlation_id,
                failed_stage="clean",
                error_type=e.__class__.__name__,
                error_message=str(e),
                tenant_id=tenant_id
            )

            raise CleanStageError(
                f"Cleaning failed: {str(e)}",
                error=str(e)
            )


# Example usage
if __name__ == "__main__":
    import asyncio

    async def test_clean_stage():
        """Test the clean stage."""
        stage = CleanStage(
            remove_urls=True,
            normalize_whitespace=True
        )
        correlation_id = str(uuid4())

        # Create test raw documents
        raw_docs = [
            RawDocument(
                id="doc-1",
                source="file_upload",
                content="""
                This   is    a    test   document.



                It has    excessive    whitespace.

                And URLs like https://example.com that should be removed.

                Email addresses like test@example.com too.
                """,
                metadata={"test": True}
            )
        ]

        try:
            # Execute clean stage
            cleaned_docs = await stage.execute(
                documents=raw_docs,
                correlation_id=correlation_id,
                job_id="job-test",
                tenant_id="tenant-test"
            )

            print(f"Cleaned {len(cleaned_docs)} document(s)\n")

            for doc in cleaned_docs:
                print(f"Document ID: {doc.id}")
                print(f"Word count: {doc.word_count}")
                print(f"Char count: {doc.char_count}")
                print(f"Reduction: {doc.metadata['reduction_percent']}%")
                print(f"\nCleaned content:\n{doc.content}\n")
                print(f"Metadata: {doc.metadata}\n")

        finally:
            await telemetry.close()

    asyncio.run(test_clean_stage())
