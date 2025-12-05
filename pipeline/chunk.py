"""
Pipeline Stage 3: CHUNK

Splits cleaned documents into semantic chunks suitable for embedding.
This is the third stage of the 5-stage pipeline.

Chunking strategies:
    - Token-based: Split by token count with overlap
    - Sentence-aware: Respect sentence boundaries
    - Paragraph-aware: Keep paragraphs together when possible

Example:
    >>> from pipeline.chunk import ChunkStage
    >>> stage = ChunkStage(chunk_size=500, overlap=50)
    >>> chunks = await stage.execute(
    ...     documents=cleaned_documents,
    ...     correlation_id="trace-123"
    ... )
"""

import logging
import re
import time
from typing import List, Optional
from uuid import uuid4

from models.document import CleanedDocument, Chunk
from services.telemetry_db_client import telemetry
from config import settings

logger = logging.getLogger(__name__)


class ChunkStageError(Exception):
    """Exception raised when chunk stage fails.

    Example:
        >>> raise ChunkStageError("Chunking failed", document_id="doc-123")
    """

    def __init__(self, message: str, **context):
        self.message = message
        self.context = context
        super().__init__(message)


class ChunkStage:
    """Stage 3: Split documents into semantic chunks.

    Creates overlapping chunks that respect sentence and paragraph boundaries
    when possible, optimized for vector embedding and semantic search.

    Attributes:
        chunk_size: Target chunk size in tokens
        overlap: Overlap size in tokens
        respect_sentences: Whether to respect sentence boundaries

    Example:
        >>> stage = ChunkStage(
        ...     chunk_size=500,
        ...     overlap=50,
        ...     respect_sentences=True
        ... )
        >>> chunks = await stage.execute(cleaned_docs, "trace-123")
    """

    def __init__(
        self,
        chunk_size: Optional[int] = None,
        overlap: Optional[int] = None,
        respect_sentences: bool = True,
        respect_paragraphs: bool = True,
        min_chunk_size: int = 50
    ):
        """Initialize chunk stage.

        Args:
            chunk_size: Target chunk size in tokens (default from settings)
            overlap: Overlap size in tokens (default from settings)
            respect_sentences: Whether to avoid splitting sentences
            respect_paragraphs: Whether to keep paragraphs together
            min_chunk_size: Minimum chunk size in tokens

        Example:
            >>> stage = ChunkStage(
            ...     chunk_size=500,
            ...     overlap=50,
            ...     respect_sentences=True
            ... )
        """
        self.chunk_size = chunk_size or settings.CHUNK_SIZE
        self.overlap = overlap or settings.CHUNK_OVERLAP
        self.respect_sentences = respect_sentences
        self.respect_paragraphs = respect_paragraphs
        self.min_chunk_size = min_chunk_size
        self.logger = logging.getLogger(__name__)

        # Validate chunk size and overlap
        if self.overlap >= self.chunk_size:
            raise ValueError(f"Overlap ({self.overlap}) must be less than chunk_size ({self.chunk_size})")

    def _estimate_tokens(self, text: str) -> int:
        """Estimate token count for text.

        Uses a simple heuristic: ~4 characters per token for English text.
        For production, consider using tiktoken for accurate counts.

        Args:
            text: Text to estimate tokens for

        Returns:
            Estimated token count

        Example:
            >>> tokens = stage._estimate_tokens("Hello world")
            >>> print(tokens)
            3
        """
        # Simple estimation: average 4 chars per token
        return max(1, len(text) // 4)

    def _split_into_sentences(self, text: str) -> List[str]:
        """Split text into sentences.

        Args:
            text: Text to split

        Returns:
            List of sentences

        Example:
            >>> sentences = stage._split_into_sentences("Hello. World. Test.")
            >>> print(len(sentences))
            3
        """
        # Simple sentence splitting (can be improved with NLTK for better accuracy)
        # Handles common sentence endings: . ! ?
        sentences = re.split(r'(?<=[.!?])\s+', text)
        return [s.strip() for s in sentences if s.strip()]

    def _split_into_paragraphs(self, text: str) -> List[str]:
        """Split text into paragraphs.

        Args:
            text: Text to split

        Returns:
            List of paragraphs

        Example:
            >>> paragraphs = stage._split_into_paragraphs("Para 1\\n\\nPara 2")
            >>> print(len(paragraphs))
            2
        """
        paragraphs = text.split('\n\n')
        return [p.strip() for p in paragraphs if p.strip()]

    def _create_chunks(
        self,
        document: CleanedDocument
    ) -> List[Chunk]:
        """Create chunks from a document.

        Args:
            document: Cleaned document to chunk

        Returns:
            List of Chunk objects

        Example:
            >>> chunks = stage._create_chunks(cleaned_doc)
            >>> print(f"Created {len(chunks)} chunks")
        """
        chunks: List[Chunk] = []
        content = document.content

        # Start with paragraphs if respect_paragraphs is True
        if self.respect_paragraphs:
            segments = self._split_into_paragraphs(content)
        elif self.respect_sentences:
            segments = self._split_into_sentences(content)
        else:
            # Simple character-based chunking
            segments = [content]

        current_chunk = []
        current_tokens = 0
        chunk_position = 0
        char_offset = 0

        for segment in segments:
            segment_tokens = self._estimate_tokens(segment)

            # If segment alone exceeds chunk_size, split it further
            if segment_tokens > self.chunk_size:
                # If we have a current chunk, save it first
                if current_chunk:
                    chunk_text = ' '.join(current_chunk) if self.respect_sentences else '\n\n'.join(current_chunk)
                    chunk_start = char_offset - len(chunk_text)
                    chunks.append(self._create_chunk(
                        document=document,
                        content=chunk_text,
                        position=chunk_position,
                        start_char=chunk_start,
                        end_char=char_offset
                    ))
                    chunk_position += 1
                    current_chunk = []
                    current_tokens = 0

                # Split large segment by sentences or characters
                if self.respect_sentences:
                    sentences = self._split_into_sentences(segment)
                    for sentence in sentences:
                        sentence_tokens = self._estimate_tokens(sentence)
                        if current_tokens + sentence_tokens > self.chunk_size and current_chunk:
                            # Save current chunk
                            chunk_text = ' '.join(current_chunk)
                            chunk_start = char_offset - len(chunk_text)
                            chunks.append(self._create_chunk(
                                document=document,
                                content=chunk_text,
                                position=chunk_position,
                                start_char=chunk_start,
                                end_char=char_offset
                            ))
                            chunk_position += 1
                            # Start new chunk with overlap
                            if self.overlap > 0 and current_chunk:
                                overlap_text = ' '.join(current_chunk[-(self.overlap//4):])
                                current_chunk = [overlap_text, sentence]
                                current_tokens = self._estimate_tokens(overlap_text) + sentence_tokens
                            else:
                                current_chunk = [sentence]
                                current_tokens = sentence_tokens
                        else:
                            current_chunk.append(sentence)
                            current_tokens += sentence_tokens
                else:
                    # Character-based splitting for very large segments
                    for i in range(0, len(segment), self.chunk_size * 4):
                        chunk_text = segment[i:i + self.chunk_size * 4]
                        chunks.append(self._create_chunk(
                            document=document,
                            content=chunk_text,
                            position=chunk_position,
                            start_char=char_offset + i,
                            end_char=char_offset + i + len(chunk_text)
                        ))
                        chunk_position += 1

                char_offset += len(segment) + 2  # +2 for paragraph separator
                continue

            # Add segment to current chunk if it fits
            if current_tokens + segment_tokens <= self.chunk_size:
                current_chunk.append(segment)
                current_tokens += segment_tokens
            else:
                # Save current chunk
                if current_chunk:
                    chunk_text = ' '.join(current_chunk) if self.respect_sentences else '\n\n'.join(current_chunk)
                    chunk_start = char_offset - len(chunk_text)
                    chunks.append(self._create_chunk(
                        document=document,
                        content=chunk_text,
                        position=chunk_position,
                        start_char=chunk_start,
                        end_char=char_offset
                    ))
                    chunk_position += 1

                # Start new chunk with overlap
                if self.overlap > 0 and current_chunk:
                    overlap_segments = current_chunk[-(max(1, len(current_chunk) // 4)):]
                    current_chunk = overlap_segments + [segment]
                    current_tokens = sum(self._estimate_tokens(s) for s in current_chunk)
                else:
                    current_chunk = [segment]
                    current_tokens = segment_tokens

            char_offset += len(segment) + 2  # +2 for paragraph separator

        # Save final chunk
        if current_chunk:
            chunk_text = ' '.join(current_chunk) if self.respect_sentences else '\n\n'.join(current_chunk)
            # Only save if above minimum size
            if self._estimate_tokens(chunk_text) >= self.min_chunk_size:
                chunk_start = max(0, char_offset - len(chunk_text))
                chunks.append(self._create_chunk(
                    document=document,
                    content=chunk_text,
                    position=chunk_position,
                    start_char=chunk_start,
                    end_char=char_offset
                ))

        return chunks

    def _create_chunk(
        self,
        document: CleanedDocument,
        content: str,
        position: int,
        start_char: int,
        end_char: int
    ) -> Chunk:
        """Create a Chunk object.

        Args:
            document: Parent document
            content: Chunk content
            position: Chunk position in document
            start_char: Start character index
            end_char: End character index

        Returns:
            Chunk object

        Example:
            >>> chunk = stage._create_chunk(doc, "text", 0, 0, 4)
        """
        return Chunk(
            document_id=document.id,
            content=content,
            metadata={
                **document.metadata,
                "chunk_strategy": "token_based",
                "chunk_size_tokens": self.chunk_size,
                "overlap_tokens": self.overlap
            },
            position=position,
            token_count=self._estimate_tokens(content),
            start_char=start_char,
            end_char=end_char,
            tenant_id=document.tenant_id
        )

    async def execute(
        self,
        documents: List[CleanedDocument],
        correlation_id: str,
        job_id: Optional[str] = None,
        tenant_id: Optional[str] = None
    ) -> List[Chunk]:
        """Execute the chunk stage.

        Splits all documents into chunks and emits telemetry.

        Args:
            documents: List of cleaned documents to chunk
            correlation_id: Distributed tracing ID
            job_id: Optional job identifier
            tenant_id: Multi-tenant identifier

        Returns:
            List of Chunk objects

        Raises:
            ChunkStageError: If chunking fails

        Example:
            >>> chunks = await stage.execute(
            ...     documents=cleaned_documents,
            ...     correlation_id="trace-123",
            ...     job_id="job-456"
            ... )
            >>> print(f"Created {len(chunks)} chunks")
        """
        start_time = time.time()
        job_id = job_id or f"job-{uuid4().hex[:12]}"

        self.logger.info(
            f"Starting chunk stage for {len(documents)} documents",
            extra={
                "correlation_id": correlation_id,
                "job_id": job_id,
                "document_count": len(documents),
                "chunk_size": self.chunk_size,
                "overlap": self.overlap,
                "tenant_id": tenant_id
            }
        )

        try:
            all_chunks: List[Chunk] = []

            for i, doc in enumerate(documents):
                self.logger.debug(
                    f"Chunking document {i+1}/{len(documents)}: {doc.id}",
                    extra={
                        "correlation_id": correlation_id,
                        "document_id": doc.id,
                        "document_index": i+1,
                        "word_count": doc.word_count
                    }
                )

                # Create chunks for this document
                doc_chunks = self._create_chunks(doc)
                all_chunks.extend(doc_chunks)

                self.logger.debug(
                    f"Created {len(doc_chunks)} chunks from document {doc.id}",
                    extra={
                        "correlation_id": correlation_id,
                        "document_id": doc.id,
                        "chunk_count": len(doc_chunks),
                        "avg_chunk_tokens": sum(c.token_count for c in doc_chunks) // len(doc_chunks) if doc_chunks else 0
                    }
                )

            # Calculate duration
            duration_ms = (time.time() - start_time) * 1000

            # Calculate statistics
            total_tokens = sum(chunk.token_count for chunk in all_chunks)
            avg_chunk_size = total_tokens / len(all_chunks) if all_chunks else 0

            # Emit telemetry
            await telemetry.emit_phase_completed(
                job_id=job_id,
                phase="chunk",
                phase_number=3,
                correlation_id=correlation_id,
                duration_ms=duration_ms,
                items_processed=len(all_chunks),
                tenant_id=tenant_id,
                metadata={
                    "document_count": len(documents),
                    "chunk_count": len(all_chunks),
                    "total_tokens": total_tokens,
                    "avg_chunk_size": round(avg_chunk_size, 2),
                    "chunks_per_document": round(len(all_chunks) / len(documents), 2) if documents else 0
                }
            )

            self.logger.info(
                f"Chunk stage completed: {len(all_chunks)} chunks in {duration_ms:.2f}ms",
                extra={
                    "correlation_id": correlation_id,
                    "job_id": job_id,
                    "chunk_count": len(all_chunks),
                    "total_tokens": total_tokens,
                    "duration_ms": duration_ms
                }
            )

            return all_chunks

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000

            self.logger.error(
                f"Chunk stage failed: {str(e)}",
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
                failed_stage="chunk",
                error_type=e.__class__.__name__,
                error_message=str(e),
                tenant_id=tenant_id
            )

            raise ChunkStageError(
                f"Chunking failed: {str(e)}",
                error=str(e)
            )


# Example usage
if __name__ == "__main__":
    import asyncio

    async def test_chunk_stage():
        """Test the chunk stage."""
        stage = ChunkStage(
            chunk_size=100,  # Small for testing
            overlap=20,
            respect_sentences=True
        )
        correlation_id = str(uuid4())

        # Create test cleaned document
        cleaned_docs = [
            CleanedDocument(
                id="doc-1",
                source="file_upload",
                content="""
                This is the first paragraph. It contains multiple sentences. Each sentence adds more content.

                This is the second paragraph. It also has several sentences. The chunker should handle this well.

                Here's a third paragraph for good measure. It helps test the chunking logic. More text means more chunks.
                """.strip(),
                metadata={"test": True},
                word_count=50,
                char_count=300
            )
        ]

        try:
            # Execute chunk stage
            chunks = await stage.execute(
                documents=cleaned_docs,
                correlation_id=correlation_id,
                job_id="job-test",
                tenant_id="tenant-test"
            )

            print(f"Created {len(chunks)} chunks\n")

            for chunk in chunks:
                print(f"Chunk {chunk.position}:")
                print(f"  ID: {chunk.id}")
                print(f"  Tokens: {chunk.token_count}")
                print(f"  Chars: {chunk.start_char}-{chunk.end_char}")
                print(f"  Content: {chunk.content[:100]}...")
                print()

        finally:
            await telemetry.close()

    asyncio.run(test_chunk_stage())
