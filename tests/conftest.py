"""Pytest Configuration and Fixtures for Rake Tests

Provides shared fixtures, test utilities, and configuration for the
Rake test suite.

Example:
    >>> # Use fixtures in tests
    >>> def test_pipeline(mock_orchestrator):
    ...     result = await mock_orchestrator.run(...)
    ...     assert result['status'] == 'completed'
"""

import asyncio
import os
import sys
from pathlib import Path
from typing import AsyncGenerator, Generator
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from main import app
from config import settings
from pipeline.orchestrator import PipelineOrchestrator
from services.telemetry_client import TelemetryClient
from services.dataforge_client import DataForgeClient
from services.embedding_service import EmbeddingService


# ============================================================================
# Pytest Configuration
# ============================================================================

def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line("markers", "unit: Unit tests")
    config.addinivalue_line("markers", "integration: Integration tests")
    config.addinivalue_line("markers", "slow: Slow tests")
    config.addinivalue_line("markers", "requires_openai: Tests requiring OpenAI API key")
    config.addinivalue_line("markers", "requires_dataforge: Tests requiring DataForge service")


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# ============================================================================
# FastAPI Test Client Fixtures
# ============================================================================

@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    """Create a FastAPI test client.

    Yields:
        TestClient instance

    Example:
        >>> def test_health(client):
        ...     response = client.get("/health")
        ...     assert response.status_code == 200
    """
    with TestClient(app) as test_client:
        yield test_client


# ============================================================================
# Mock Service Fixtures
# ============================================================================

@pytest.fixture
def mock_telemetry() -> TelemetryClient:
    """Create a mock telemetry client.

    Returns:
        Mocked TelemetryClient

    Example:
        >>> def test_job(mock_telemetry):
        ...     await mock_telemetry.emit_job_started(...)
    """
    telemetry = TelemetryClient(enabled=False)
    return telemetry


@pytest.fixture
def mock_dataforge() -> MagicMock:
    """Create a mock DataForge client.

    Returns:
        Mocked DataForgeClient

    Example:
        >>> async def test_store(mock_dataforge):
        ...     mock_dataforge.store_embeddings.return_value = {"status": "success"}
        ...     result = await store_stage(...)
    """
    mock = MagicMock(spec=DataForgeClient)
    mock.store_embeddings = AsyncMock(return_value={"status": "success", "count": 10})
    mock.query_knowledge_base = AsyncMock(return_value={"results": []})
    return mock


@pytest.fixture
def mock_embedding_service() -> MagicMock:
    """Create a mock embedding service.

    Returns:
        Mocked EmbeddingService

    Example:
        >>> async def test_embed(mock_embedding_service):
        ...     mock_embedding_service.generate_embeddings.return_value = [...]
    """
    mock = MagicMock(spec=EmbeddingService)
    # Return mock embeddings (1536 dimensions for text-embedding-3-small)
    mock.generate_embeddings = AsyncMock(
        return_value=[[0.1] * 1536 for _ in range(10)]
    )
    return mock


@pytest.fixture
def mock_orchestrator() -> MagicMock:
    """Create a mock pipeline orchestrator.

    Returns:
        Mocked PipelineOrchestrator

    Example:
        >>> async def test_job(mock_orchestrator):
        ...     mock_orchestrator.run.return_value = {"status": "completed"}
    """
    mock = MagicMock(spec=PipelineOrchestrator)
    mock.run = AsyncMock(
        return_value={
            "job_id": "job-test-123",
            "status": "completed",
            "documents_stored": 5,
            "chunks_created": 25,
            "embeddings_generated": 25,
            "duration_ms": 1500.0,
            "stages_completed": ["fetch", "clean", "chunk", "embed", "store"]
        }
    )
    mock.close = AsyncMock()
    return mock


# ============================================================================
# Sample Data Fixtures
# ============================================================================

@pytest.fixture
def sample_text() -> str:
    """Provide sample text for testing.

    Returns:
        Sample document text

    Example:
        >>> def test_clean(sample_text):
        ...     cleaned = clean_text(sample_text)
        ...     assert len(cleaned) > 0
    """
    return """
    This is a sample document for testing the Rake pipeline.

    It contains multiple paragraphs with various content types.
    The text includes punctuation, numbers (123), and special characters!

    We can test text processing, chunking, and embedding with this content.
    """


@pytest.fixture
def sample_html() -> str:
    """Provide sample HTML for testing.

    Returns:
        Sample HTML content

    Example:
        >>> def test_html_removal(sample_html):
        ...     cleaned = remove_html_tags(sample_html)
        ...     assert "<" not in cleaned
    """
    return """
    <html>
        <body>
            <h1>Test Document</h1>
            <p>This is a <strong>test</strong> paragraph.</p>
            <ul>
                <li>Item 1</li>
                <li>Item 2</li>
            </ul>
        </body>
    </html>
    """


@pytest.fixture
def sample_pdf_path(tmp_path) -> Path:
    """Create a sample text file (simulating PDF).

    Args:
        tmp_path: Pytest temporary directory fixture

    Returns:
        Path to sample file

    Example:
        >>> def test_fetch(sample_pdf_path):
        ...     result = await fetch_stage("file_upload", file_path=str(sample_pdf_path))
        ...     assert len(result) > 0
    """
    file_path = tmp_path / "test_document.txt"
    file_path.write_text("This is test document content for the Rake pipeline.")
    return file_path


@pytest.fixture
def sample_chunks() -> list[dict]:
    """Provide sample chunks for testing.

    Returns:
        List of chunk dictionaries

    Example:
        >>> async def test_embed(sample_chunks, mock_embedding_service):
        ...     embeddings = await embed_stage(sample_chunks)
    """
    return [
        {
            "id": "chunk-1",
            "document_id": "doc-test-1",
            "content": "First chunk of text content.",
            "position": 0,
            "token_count": 10
        },
        {
            "id": "chunk-2",
            "document_id": "doc-test-1",
            "content": "Second chunk of text content.",
            "position": 1,
            "token_count": 10
        }
    ]


# ============================================================================
# Environment Fixtures
# ============================================================================

@pytest.fixture
def test_env(monkeypatch):
    """Set test environment variables.

    Args:
        monkeypatch: Pytest monkeypatch fixture

    Example:
        >>> def test_config(test_env):
        ...     assert settings.ENVIRONMENT == "testing"
    """
    monkeypatch.setenv("ENVIRONMENT", "testing")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key")
    monkeypatch.setenv("DATABASE_URL", "postgresql://test:test@localhost/test")


# ============================================================================
# Cleanup Fixtures
# ============================================================================

@pytest.fixture(autouse=True)
def reset_context():
    """Reset tenant context after each test.

    Automatically runs after every test to ensure clean state.
    """
    yield
    # Cleanup after test
    from auth.tenant_context import clear_tenant_context
    clear_tenant_context()


# ============================================================================
# Helper Functions
# ============================================================================

def assert_valid_job_response(response: dict) -> None:
    """Assert that a job response has required fields.

    Args:
        response: Job response dictionary

    Example:
        >>> response = client.post("/api/v1/jobs", json={...}).json()
        >>> assert_valid_job_response(response)
    """
    required_fields = [
        "job_id",
        "status",
        "source",
        "created_at"
    ]
    for field in required_fields:
        assert field in response, f"Missing required field: {field}"


def create_test_job_request(
    source: str = "file_upload",
    tenant_id: str = "tenant-test"
) -> dict:
    """Create a test job submission request.

    Args:
        source: Source type
        tenant_id: Tenant identifier

    Returns:
        Job request dictionary

    Example:
        >>> request = create_test_job_request()
        >>> response = client.post("/api/v1/jobs", json=request)
    """
    return {
        "source": source,
        "tenant_id": tenant_id,
        "file_path": "/tmp/test.txt" if source == "file_upload" else None,
        "url": "https://example.com" if source == "url_scrape" else None,
    }
