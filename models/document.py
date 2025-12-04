"""
Document Data Models for Rake Pipeline

Pydantic v2 models representing documents at each stage of the 5-stage pipeline:
    1. RawDocument (after FETCH)
    2. CleanedDocument (after CLEAN)
    3. Chunk (after CHUNK)
    4. Embedding (after EMBED)
    5. StoredDocument (after STORE)

All models include comprehensive validation and example usage.

Example:
    >>> from models.document import RawDocument
    >>> doc = RawDocument(
    ...     id="doc-123",
    ...     source="file_upload",
    ...     content="Sample content",
    ...     metadata={"filename": "test.pdf"}
    ... )
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator, ConfigDict


class DocumentSource(str, Enum):
    """Source types for document ingestion.

    Attributes:
        FILE_UPLOAD: Direct file upload (PDF, DOCX, TXT)
        URL_SCRAPE: Web scraping from URL
        API_FETCH: External API integration
        DATABASE_QUERY: Database query results
        SCHEDULED_JOB: Scheduled ingestion task

    Example:
        >>> source = DocumentSource.FILE_UPLOAD
        >>> print(source.value)
        file_upload
    """
    FILE_UPLOAD = "file_upload"
    URL_SCRAPE = "url_scrape"
    API_FETCH = "api_fetch"
    DATABASE_QUERY = "database_query"
    SCHEDULED_JOB = "scheduled_job"


class ProcessingStatus(str, Enum):
    """Processing status for pipeline jobs.

    Attributes:
        PENDING: Job created, not yet started
        FETCHING: Stage 1 in progress
        CLEANING: Stage 2 in progress
        CHUNKING: Stage 3 in progress
        EMBEDDING: Stage 4 in progress
        STORING: Stage 5 in progress
        COMPLETED: Pipeline completed successfully
        FAILED: Pipeline failed at some stage
        RETRYING: Retrying after failure

    Example:
        >>> status = ProcessingStatus.COMPLETED
        >>> if status == ProcessingStatus.COMPLETED:
        ...     print("Job finished!")
    """
    PENDING = "pending"
    FETCHING = "fetching"
    CLEANING = "cleaning"
    CHUNKING = "chunking"
    EMBEDDING = "embedding"
    STORING = "storing"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"


class RawDocument(BaseModel):
    """Document after FETCH stage (Stage 1).

    Represents a document immediately after fetching from a source,
    before any cleaning or processing.

    Attributes:
        id: Unique document identifier
        source: Source type (file_upload, url_scrape, etc.)
        url: Optional source URL
        content: Raw document content
        metadata: Additional metadata (filename, author, etc.)
        fetched_at: Timestamp when document was fetched
        tenant_id: Multi-tenant identifier

    Example:
        >>> doc = RawDocument(
        ...     id="doc-123",
        ...     source=DocumentSource.FILE_UPLOAD,
        ...     content="Raw PDF content...",
        ...     metadata={"filename": "report.pdf", "size_bytes": 12345},
        ...     tenant_id="tenant-abc"
        ... )
        >>> print(f"Fetched {doc.metadata['filename']} with {len(doc.content)} chars")
    """

    model_config = ConfigDict(use_enum_values=True)

    id: str = Field(default_factory=lambda: f"doc-{uuid4().hex[:12]}")
    source: DocumentSource
    url: Optional[str] = None
    content: str = Field(..., min_length=1)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    fetched_at: datetime = Field(default_factory=datetime.utcnow)
    tenant_id: Optional[str] = None

    @field_validator("content")
    @classmethod
    def validate_content_not_empty(cls, v: str) -> str:
        """Ensure content is not just whitespace.

        Args:
            v: Content string

        Returns:
            Validated content

        Raises:
            ValueError: If content is empty or whitespace only
        """
        if not v.strip():
            raise ValueError("Document content cannot be empty or whitespace only")
        return v


class CleanedDocument(BaseModel):
    """Document after CLEAN stage (Stage 2).

    Represents a document after text normalization and cleaning.

    Attributes:
        id: Document identifier (same as RawDocument.id)
        source: Original source type
        content: Cleaned and normalized content
        metadata: Enriched metadata
        word_count: Number of words in cleaned content
        char_count: Number of characters in cleaned content
        cleaned_at: Timestamp when cleaning completed
        tenant_id: Multi-tenant identifier

    Example:
        >>> doc = CleanedDocument(
        ...     id="doc-123",
        ...     source=DocumentSource.FILE_UPLOAD,
        ...     content="This is clean text.",
        ...     metadata={"language": "en"},
        ...     word_count=4,
        ...     char_count=19,
        ...     tenant_id="tenant-abc"
        ... )
    """

    model_config = ConfigDict(use_enum_values=True)

    id: str
    source: DocumentSource
    content: str = Field(..., min_length=1)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    word_count: int = Field(ge=0)
    char_count: int = Field(ge=0)
    cleaned_at: datetime = Field(default_factory=datetime.utcnow)
    tenant_id: Optional[str] = None


class Chunk(BaseModel):
    """Document chunk after CHUNK stage (Stage 3).

    Represents a semantic segment of a document, ready for embedding.

    Attributes:
        id: Unique chunk identifier
        document_id: Parent document ID
        content: Chunk text content
        metadata: Chunk metadata (position, overlap info, etc.)
        position: Chunk position in document (0-indexed)
        token_count: Number of tokens in chunk
        start_char: Starting character index in original document
        end_char: Ending character index in original document
        created_at: Timestamp when chunk was created
        tenant_id: Multi-tenant identifier

    Example:
        >>> chunk = Chunk(
        ...     id="chunk-123",
        ...     document_id="doc-123",
        ...     content="First paragraph of document...",
        ...     position=0,
        ...     token_count=45,
        ...     start_char=0,
        ...     end_char=150,
        ...     tenant_id="tenant-abc"
        ... )
    """

    id: str = Field(default_factory=lambda: f"chunk-{uuid4().hex[:12]}")
    document_id: str
    content: str = Field(..., min_length=1)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    position: int = Field(ge=0)
    token_count: int = Field(ge=1)
    start_char: int = Field(ge=0)
    end_char: int = Field(gt=0)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    tenant_id: Optional[str] = None

    @field_validator("end_char")
    @classmethod
    def validate_end_after_start(cls, v: int, info) -> int:
        """Ensure end_char is greater than start_char.

        Args:
            v: end_char value
            info: Validation context with other field values

        Returns:
            Validated end_char

        Raises:
            ValueError: If end_char <= start_char
        """
        start_char = info.data.get("start_char", 0)
        if v <= start_char:
            raise ValueError(f"end_char ({v}) must be greater than start_char ({start_char})")
        return v


class Embedding(BaseModel):
    """Vector embedding after EMBED stage (Stage 4).

    Represents a chunk's vector embedding generated by OpenAI.

    Attributes:
        id: Unique embedding identifier
        chunk_id: Parent chunk ID
        vector: Embedding vector (1536 dimensions for text-embedding-3-small)
        model: OpenAI model used for embedding
        metadata: Additional metadata (model version, etc.)
        created_at: Timestamp when embedding was created
        tenant_id: Multi-tenant identifier

    Example:
        >>> embedding = Embedding(
        ...     id="emb-123",
        ...     chunk_id="chunk-123",
        ...     vector=[0.1, 0.2, ..., 0.5],  # 1536 dimensions
        ...     model="text-embedding-3-small",
        ...     tenant_id="tenant-abc"
        ... )
        >>> print(f"Embedding has {len(embedding.vector)} dimensions")
    """

    id: str = Field(default_factory=lambda: f"emb-{uuid4().hex[:12]}")
    chunk_id: str
    vector: List[float] = Field(..., min_length=1)
    model: str = "text-embedding-3-small"
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    tenant_id: Optional[str] = None

    @field_validator("vector")
    @classmethod
    def validate_vector_dimensions(cls, v: List[float]) -> List[float]:
        """Validate embedding vector dimensions.

        OpenAI text-embedding-3-small produces 1536 dimensions.

        Args:
            v: Vector list

        Returns:
            Validated vector

        Raises:
            ValueError: If vector dimensions are invalid
        """
        expected_dims = 1536
        if len(v) != expected_dims:
            raise ValueError(
                f"Embedding vector must have {expected_dims} dimensions, got {len(v)}"
            )
        return v


class StoredDocument(BaseModel):
    """Document metadata after STORE stage (Stage 5).

    Represents the final stored document record in DataForge.
    Does not include full content or embeddings (those are in separate tables).

    Attributes:
        id: Document identifier
        source: Original source type
        url: Optional source URL
        metadata: Document metadata
        chunk_count: Number of chunks created
        embedding_count: Number of embeddings generated
        status: Current processing status
        error_message: Error message if failed
        created_at: Original creation timestamp
        stored_at: Timestamp when stored in DataForge
        tenant_id: Multi-tenant identifier

    Example:
        >>> stored = StoredDocument(
        ...     id="doc-123",
        ...     source=DocumentSource.FILE_UPLOAD,
        ...     metadata={"filename": "report.pdf"},
        ...     chunk_count=10,
        ...     embedding_count=10,
        ...     status=ProcessingStatus.COMPLETED,
        ...     tenant_id="tenant-abc"
        ... )
    """

    model_config = ConfigDict(use_enum_values=True)

    id: str
    source: DocumentSource
    url: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    chunk_count: int = Field(ge=0)
    embedding_count: int = Field(ge=0)
    status: ProcessingStatus = ProcessingStatus.COMPLETED
    error_message: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    stored_at: datetime = Field(default_factory=datetime.utcnow)
    tenant_id: Optional[str] = None


class PipelineJob(BaseModel):
    """Pipeline job tracking the entire 5-stage process.

    Tracks a document through all 5 stages of the pipeline.

    Attributes:
        job_id: Unique job identifier
        document_id: Document being processed
        source: Document source type
        status: Current processing status
        current_stage: Current stage (1-5)
        stages_completed: List of completed stage names
        error_message: Error message if failed
        retry_count: Number of retries attempted
        metadata: Job metadata
        started_at: Job start timestamp
        completed_at: Job completion timestamp
        tenant_id: Multi-tenant identifier
        correlation_id: Distributed tracing ID

    Example:
        >>> job = PipelineJob(
        ...     job_id="job-123",
        ...     document_id="doc-123",
        ...     source=DocumentSource.FILE_UPLOAD,
        ...     status=ProcessingStatus.CHUNKING,
        ...     current_stage=3,
        ...     stages_completed=["fetch", "clean"],
        ...     correlation_id="trace-abc",
        ...     tenant_id="tenant-abc"
        ... )
    """

    model_config = ConfigDict(use_enum_values=True)

    job_id: str = Field(default_factory=lambda: f"job-{uuid4().hex[:12]}")
    document_id: str
    source: DocumentSource
    status: ProcessingStatus = ProcessingStatus.PENDING
    current_stage: int = Field(default=0, ge=0, le=5)
    stages_completed: List[str] = Field(default_factory=list)
    error_message: Optional[str] = None
    retry_count: int = Field(default=0, ge=0)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    tenant_id: Optional[str] = None
    correlation_id: str = Field(default_factory=lambda: str(uuid4()))

    @property
    def is_complete(self) -> bool:
        """Check if job has completed (success or failure).

        Returns:
            True if job is completed or failed

        Example:
            >>> job = PipelineJob(status=ProcessingStatus.COMPLETED, ...)
            >>> if job.is_complete:
            ...     print("Job finished!")
        """
        return self.status in [ProcessingStatus.COMPLETED, ProcessingStatus.FAILED]

    @property
    def is_successful(self) -> bool:
        """Check if job completed successfully.

        Returns:
            True if job status is COMPLETED

        Example:
            >>> job = PipelineJob(status=ProcessingStatus.COMPLETED, ...)
            >>> if job.is_successful:
            ...     print("Success!")
        """
        return self.status == ProcessingStatus.COMPLETED

    @property
    def duration_seconds(self) -> Optional[float]:
        """Calculate job duration in seconds.

        Returns:
            Duration in seconds if completed, None otherwise

        Example:
            >>> job = PipelineJob(...)
            >>> if job.duration_seconds:
            ...     print(f"Took {job.duration_seconds:.2f} seconds")
        """
        if self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None


# Example usage and testing
if __name__ == "__main__":
    # Example: Create a raw document
    raw_doc = RawDocument(
        source=DocumentSource.FILE_UPLOAD,
        content="This is a sample PDF document with multiple paragraphs.",
        metadata={
            "filename": "sample.pdf",
            "size_bytes": 1024,
            "mime_type": "application/pdf"
        },
        tenant_id="tenant-123"
    )
    print(f"Created RawDocument: {raw_doc.id}")

    # Example: Create a cleaned document
    cleaned_doc = CleanedDocument(
        id=raw_doc.id,
        source=raw_doc.source,
        content="This is a sample PDF document with multiple paragraphs.",
        word_count=9,
        char_count=52,
        metadata={**raw_doc.metadata, "language": "en"},
        tenant_id=raw_doc.tenant_id
    )
    print(f"Cleaned document: {cleaned_doc.word_count} words")

    # Example: Create a chunk
    chunk = Chunk(
        document_id=cleaned_doc.id,
        content="This is a sample PDF document",
        position=0,
        token_count=7,
        start_char=0,
        end_char=30,
        tenant_id=raw_doc.tenant_id
    )
    print(f"Created chunk: {chunk.id} with {chunk.token_count} tokens")

    # Example: Track pipeline job
    job = PipelineJob(
        document_id=raw_doc.id,
        source=raw_doc.source,
        status=ProcessingStatus.CHUNKING,
        current_stage=3,
        stages_completed=["fetch", "clean"],
        tenant_id=raw_doc.tenant_id
    )
    print(f"Job {job.job_id} is at stage {job.current_stage}")
    print(f"Completed stages: {', '.join(job.stages_completed)}")
