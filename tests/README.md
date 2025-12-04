# Rake Test Suite

Comprehensive test suite for the Rake data ingestion pipeline.

## Test Structure

```
tests/
├── conftest.py              # Shared fixtures and configuration
├── unit/                    # Unit tests (fast, isolated)
│   ├── test_text_processing.py
│   ├── test_retry.py
│   ├── test_jwt_handler.py
│   ├── test_tenant_context.py
│   └── ...
├── integration/             # Integration tests (slower, external deps)
│   ├── test_api_endpoints.py
│   ├── test_pipeline.py
│   └── ...
└── README.md               # This file
```

## Running Tests

### Run All Tests

```bash
pytest
```

### Run with Coverage

```bash
pytest --cov=. --cov-report=html
# Open htmlcov/index.html to view report
```

### Run Specific Test File

```bash
pytest tests/unit/test_text_processing.py -v
```

### Run by Marker

```bash
# Unit tests only (fast)
pytest -m unit

# Integration tests only
pytest -m integration

# Exclude slow tests
pytest -m "not slow"
```

### Run with Output

```bash
# Show print statements
pytest -s

# Verbose output
pytest -v

# Very verbose (show test names)
pytest -vv
```

## Test Categories

### Unit Tests (`-m unit`)

Fast, isolated tests that don't require external services:
- Text processing utilities
- Retry logic
- JWT authentication
- Configuration validation
- Model validation

### Integration Tests (`-m integration`)

Tests that interact with multiple components:
- API endpoints
- Pipeline orchestration
- Database operations (requires PostgreSQL)
- External service mocks

### Slow Tests (`-m slow`)

Long-running tests (>1 second):
- End-to-end pipeline tests
- Large file processing
- Scheduled job tests

### External Dependency Tests

Tests requiring external services:
- `requires_openai`: Needs OpenAI API key
- `requires_dataforge`: Needs DataForge service running

Skip these with:
```bash
pytest -m "not requires_openai and not requires_dataforge"
```

## Writing Tests

### Unit Test Example

```python
import pytest
from utils.text_processing import clean_text

def test_clean_html():
    """Test HTML tag removal."""
    html = "<p>Hello <strong>World</strong>!</p>"
    result = clean_text(html)
    assert "<" not in result
    assert "Hello World" in result
```

### Integration Test Example

```python
import pytest

@pytest.mark.integration
async def test_pipeline(client, sample_pdf_path):
    """Test complete pipeline execution."""
    response = client.post("/api/v1/jobs", json={
        "source": "file_upload",
        "file_path": str(sample_pdf_path),
        "tenant_id": "tenant-test"
    })
    assert response.status_code == 202
```

### Using Fixtures

```python
def test_with_mock_services(mock_telemetry, mock_dataforge):
    """Test using mocked services."""
    # mock_telemetry and mock_dataforge are automatically provided
    # by conftest.py fixtures
    pass
```

## Fixtures Available

### Service Mocks

- `mock_telemetry`: Mocked TelemetryClient
- `mock_dataforge`: Mocked DataForgeClient
- `mock_embedding_service`: Mocked EmbeddingService
- `mock_orchestrator`: Mocked PipelineOrchestrator

### Sample Data

- `sample_text`: Plain text for testing
- `sample_html`: HTML content for testing
- `sample_pdf_path`: Temporary PDF file path
- `sample_chunks`: List of text chunks

### FastAPI Client

- `client`: TestClient for API testing

## Coverage Goals

Target: **80%+ code coverage**

Current coverage by module:
```
# TODO: Run pytest --cov to generate actual coverage report
utils/           - Target: 90%
auth/            - Target: 85%
pipeline/        - Target: 80%
services/        - Target: 75%
api/             - Target: 85%
```

## Continuous Integration

Tests are run automatically on:
- Every commit (fast tests only)
- Pull requests (all tests)
- Nightly (all tests including slow)

## Troubleshooting

### Import Errors

If you get import errors, ensure you're running from the rake directory:
```bash
cd /path/to/rake
pytest
```

### Async Test Errors

Make sure pytest-asyncio is installed:
```bash
pip install pytest-asyncio
```

### Database Connection Errors

For tests requiring PostgreSQL, ensure the database is running:
```bash
docker run -d -p 5432:5432 -e POSTGRES_PASSWORD=test postgres:14
```

Or skip database tests:
```bash
pytest -m "not requires_database"
```

## Best Practices

1. **Use descriptive test names**: `test_clean_removes_html_tags`
2. **One assertion per test** (when possible)
3. **Use fixtures** instead of setup/teardown
4. **Mark slow tests**: `@pytest.mark.slow`
5. **Mock external services** to avoid flaky tests
6. **Test edge cases**: empty inputs, large inputs, invalid data
7. **Use parametrize** for testing multiple inputs:

```python
@pytest.mark.parametrize("input,expected", [
    ("hello", "HELLO"),
    ("world", "WORLD"),
])
def test_uppercase(input, expected):
    assert input.upper() == expected
```

## Adding New Tests

1. Create test file in appropriate directory (unit/ or integration/)
2. Name file `test_<module_name>.py`
3. Import pytest and module under test
4. Write test classes/functions
5. Add appropriate markers
6. Update this README if needed

## Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [FastAPI Testing](https://fastapi.tiangolo.com/tutorial/testing/)
- [pytest-asyncio](https://pytest-asyncio.readthedocs.io/)
