# Contributing to Rake V1

Thank you for your interest in contributing to Rake! This document provides guidelines and best practices for contributing to the project.

---

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Workflow](#development-workflow)
- [Coding Standards](#coding-standards)
- [Testing Requirements](#testing-requirements)
- [Documentation](#documentation)
- [Pull Request Process](#pull-request-process)
- [Release Process](#release-process)

---

## Code of Conduct

### Our Pledge

We are committed to providing a welcoming and inclusive environment for all contributors. Please treat others with respect and professionalism.

### Expected Behavior

- Use welcoming and inclusive language
- Be respectful of differing viewpoints and experiences
- Gracefully accept constructive criticism
- Focus on what is best for the project and community
- Show empathy towards other community members

---

## Getting Started

### Prerequisites

- **Python 3.11+** (required)
- **PostgreSQL 14+** (for integration tests)
- **Git** (version control)
- **Docker** (optional, for DataForge testing)

### Development Setup

```bash
# 1. Fork and clone the repository
git clone https://github.com/yourusername/rake.git
cd rake

# 2. Create virtual environment
python3.11 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt  # Development dependencies

# 4. Install pre-commit hooks
pre-commit install

# 5. Copy environment template
cp .env.example .env
# Edit .env with your configuration

# 6. Run tests to verify setup
pytest
```

### Development Dependencies

```bash
# requirements-dev.txt
pytest==7.4.3
pytest-asyncio==0.21.1
pytest-cov==4.1.0
black==23.11.0
isort==5.12.0
flake8==6.1.0
mypy==1.7.1
pre-commit==3.5.0
```

---

## Development Workflow

### Branch Strategy

We use **Git Flow** branching model:

```
main (production)
  └── develop (integration)
       ├── feature/your-feature
       ├── fix/bug-description
       └── docs/documentation-update
```

### Creating a Feature Branch

```bash
# Start from develop branch
git checkout develop
git pull origin develop

# Create feature branch
git checkout -b feature/your-feature-name

# Make changes, commit frequently
git add .
git commit -m "feat: add your feature description"

# Push to your fork
git push origin feature/your-feature-name
```

### Commit Message Convention

We follow **Conventional Commits** specification:

```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `test`: Adding or updating tests
- `refactor`: Code refactoring
- `perf`: Performance improvements
- `chore`: Maintenance tasks
- `ci`: CI/CD changes

**Examples:**
```bash
feat(api): add job cancellation endpoint
fix(embed): handle empty chunk lists
docs(readme): update installation instructions
test(database): add tests for job listing
refactor(pipeline): simplify error handling
```

---

## Coding Standards

### Python Style Guide

We follow **PEP 8** with some modifications:

```python
# Line length: 100 characters (not 79)
# Use double quotes for strings
# Use trailing commas in multi-line collections

# Good
def process_document(
    document_id: str,
    tenant_id: str,
    options: Optional[Dict[str, Any]] = None,
) -> ProcessedDocument:
    """Process a document with optional parameters.

    Args:
        document_id: Unique document identifier
        tenant_id: Tenant identifier for multi-tenancy
        options: Optional processing options

    Returns:
        ProcessedDocument instance

    Raises:
        ValueError: If document_id is invalid
        ProcessingError: If processing fails
    """
    if not document_id:
        raise ValueError("document_id cannot be empty")

    # Implementation here
    pass
```

### Type Hints

**Always use type hints** for function signatures:

```python
from typing import List, Dict, Optional, Any

# Good ✅
async def fetch_documents(
    source: str,
    tenant_id: str,
    limit: Optional[int] = None
) -> List[Document]:
    pass

# Bad ❌
async def fetch_documents(source, tenant_id, limit=None):
    pass
```

### Docstrings

Use **Google-style docstrings**:

```python
def create_chunks(
    text: str,
    chunk_size: int = 500,
    overlap: int = 100
) -> List[Chunk]:
    """Split text into overlapping chunks.

    Creates semantic chunks with configurable size and overlap
    for optimal embedding generation.

    Args:
        text: Input text to chunk
        chunk_size: Maximum tokens per chunk (default: 500)
        overlap: Token overlap between chunks (default: 100)

    Returns:
        List of Chunk objects with content and metadata

    Raises:
        ValueError: If chunk_size < 1 or overlap >= chunk_size

    Example:
        >>> chunks = create_chunks("Long text here", chunk_size=100)
        >>> len(chunks)
        3
    """
    pass
```

### Code Formatting

We use **Black** and **isort** for automatic formatting:

```bash
# Format code
black .

# Sort imports
isort .

# Both are run automatically via pre-commit hooks
```

### Linting

We use **flake8** and **mypy** for linting:

```bash
# Run flake8
flake8 .

# Run mypy
mypy .

# Configuration in setup.cfg and pyproject.toml
```

---

## Testing Requirements

### Test Coverage

**Minimum required coverage: 80%**

```bash
# Run tests with coverage
pytest --cov=. --cov-report=html

# View coverage report
open htmlcov/index.html
```

### Writing Tests

#### Unit Tests

Fast, isolated tests for individual functions:

```python
# tests/unit/test_text_processing.py
import pytest
from utils.text_processing import clean_text, remove_html

def test_clean_text_removes_html():
    """Test HTML tag removal."""
    html = "<p>Hello <strong>World</strong>!</p>"
    result = clean_text(html)
    assert "<" not in result
    assert "Hello World" in result

def test_clean_text_normalizes_whitespace():
    """Test whitespace normalization."""
    text = "Hello    World\n\n\nFoo"
    result = clean_text(text)
    assert result == "Hello World Foo"
```

#### Integration Tests

Tests involving multiple components:

```python
# tests/integration/test_pipeline.py
import pytest

@pytest.mark.integration
async def test_complete_pipeline(test_db, mock_dataforge):
    """Test full pipeline execution."""
    from pipeline.orchestrator import PipelineOrchestrator

    orchestrator = PipelineOrchestrator(
        db=test_db,
        dataforge=mock_dataforge
    )

    result = await orchestrator.run(
        job_id="test-123",
        source="file_upload",
        tenant_id="tenant-test",
        file_path="/tmp/test.txt"
    )

    assert result["status"] == "completed"
    assert result["chunks_created"] > 0
```

#### Test Markers

Use pytest markers to categorize tests:

```python
@pytest.mark.unit
def test_fast_function():
    """Fast unit test."""
    pass

@pytest.mark.integration
async def test_database_operation():
    """Integration test requiring database."""
    pass

@pytest.mark.slow
async def test_large_file_processing():
    """Slow test (>1 second)."""
    pass

@pytest.mark.requires_openai
async def test_embedding_generation():
    """Test requiring OpenAI API key."""
    pass
```

Run specific test types:

```bash
# Only unit tests (fast)
pytest -m unit

# Skip slow tests
pytest -m "not slow"

# Skip external dependencies
pytest -m "not requires_openai and not requires_dataforge"
```

### Test File Organization

```
tests/
├── conftest.py              # Shared fixtures
├── unit/                    # Unit tests
│   ├── test_text_processing.py
│   ├── test_retry.py
│   ├── test_jwt_handler.py
│   ├── test_database_service.py
│   └── ...
├── integration/             # Integration tests
│   ├── test_api_endpoints.py
│   ├── test_pipeline.py
│   └── ...
└── README.md               # Test documentation
```

---

## Documentation

### Code Documentation

1. **Docstrings**: All public functions, classes, and modules
2. **Type Hints**: All function signatures
3. **Comments**: Complex logic only (code should be self-documenting)

### User Documentation

When adding features, update:

1. [README.md](README.md) - If feature changes core functionality
2. [QUICKSTART.md](QUICKSTART.md) - If setup process changes
3. Feature-specific guides in [docs/](docs/) - For new data sources or major features
4. [ARCHITECTURE.md](docs/ARCHITECTURE.md) - If architecture changes

### Documentation Style

- Use **Markdown** for all documentation
- Include **code examples** where helpful
- Add **diagrams** for complex workflows (ASCII or Mermaid)
- Keep documentation **up to date** with code changes

---

## Pull Request Process

### Before Submitting

- [ ] All tests pass (`pytest`)
- [ ] Code coverage ≥ 80% (`pytest --cov`)
- [ ] Code is formatted (`black . && isort .`)
- [ ] Linting passes (`flake8 . && mypy .`)
- [ ] Documentation is updated
- [ ] Commit messages follow convention
- [ ] Branch is up to date with `develop`

### PR Checklist

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix (non-breaking change which fixes an issue)
- [ ] New feature (non-breaking change which adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] Documentation update

## Testing
- [ ] Unit tests added/updated
- [ ] Integration tests added/updated
- [ ] All tests passing locally
- [ ] Coverage ≥ 80%

## Documentation
- [ ] README.md updated (if needed)
- [ ] Docstrings added/updated
- [ ] Type hints added
- [ ] Guides updated (if applicable)

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Comments added for complex logic
- [ ] No new warnings introduced
- [ ] Branch is up to date with develop
```

### PR Review Process

1. **Automated Checks**: CI/CD runs tests, linting, coverage
2. **Code Review**: At least one maintainer reviews code
3. **Feedback**: Address review comments
4. **Approval**: Maintainer approves PR
5. **Merge**: Squash and merge to `develop`

### Review Criteria

Reviewers check for:

- **Correctness**: Does the code work as intended?
- **Tests**: Are there adequate tests?
- **Documentation**: Is it well-documented?
- **Style**: Does it follow coding standards?
- **Performance**: Are there any performance issues?
- **Security**: Are there any security concerns?

---

## Release Process

### Version Numbering

We use **Semantic Versioning** (SemVer):

```
MAJOR.MINOR.PATCH

1.0.0 → 1.1.0 (new feature)
1.1.0 → 1.1.1 (bug fix)
1.1.1 → 2.0.0 (breaking change)
```

### Release Workflow

```bash
# 1. Update version in relevant files
# - config.py (VERSION constant)
# - setup.py (if applicable)

# 2. Update CHANGELOG.md
# - Add release notes for new version

# 3. Create release branch
git checkout -b release/v1.1.0

# 4. Final testing
pytest --cov

# 5. Merge to main
git checkout main
git merge release/v1.1.0

# 6. Tag release
git tag -a v1.1.0 -m "Release version 1.1.0"
git push origin v1.1.0

# 7. Merge back to develop
git checkout develop
git merge main
```

---

## Development Tools

### Recommended IDE Setup

**VS Code Extensions:**
- Python (Microsoft)
- Pylance (Microsoft)
- Black Formatter
- isort
- autoDocstring
- Python Test Explorer

**Settings (`settings.json`):**
```json
{
  "python.linting.enabled": true,
  "python.linting.flake8Enabled": true,
  "python.formatting.provider": "black",
  "python.formatting.blackArgs": ["--line-length", "100"],
  "editor.formatOnSave": true,
  "python.testing.pytestEnabled": true,
  "[python]": {
    "editor.codeActionsOnSave": {
      "source.organizeImports": true
    }
  }
}
```

### Debugging

```python
# Add breakpoint in code
import pdb; pdb.set_trace()

# Or use VS Code debugger (launch.json)
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Python: FastAPI",
      "type": "python",
      "request": "launch",
      "module": "uvicorn",
      "args": ["main:app", "--reload", "--port", "8002"],
      "jinja": true
    },
    {
      "name": "Python: Pytest",
      "type": "python",
      "request": "launch",
      "module": "pytest",
      "args": ["-v"]
    }
  ]
}
```

---

## Getting Help

### Resources

- **Documentation**: [README.md](README.md), [docs/](docs/)
- **Issues**: [GitHub Issues](https://github.com/yourusername/rake/issues)
- **Discussions**: [GitHub Discussions](https://github.com/yourusername/rake/discussions)

### Reporting Bugs

Use the bug report template:

```markdown
**Describe the bug**
A clear description of what the bug is.

**To Reproduce**
Steps to reproduce the behavior:
1. Run command '...'
2. See error '...'

**Expected behavior**
What you expected to happen.

**Environment:**
- OS: [e.g. Ubuntu 22.04]
- Python version: [e.g. 3.11.5]
- Rake version: [e.g. 1.0.0]

**Additional context**
Logs, screenshots, or other context.
```

### Suggesting Features

Use the feature request template:

```markdown
**Feature Description**
Clear description of the proposed feature.

**Use Case**
Why is this feature needed?

**Proposed Solution**
How should this feature work?

**Alternatives Considered**
Other approaches you've considered.

**Additional context**
Mockups, examples, or references.
```

---

## License

By contributing to Rake, you agree that your contributions will be licensed under the same license as the project.

---

## Questions?

If you have questions about contributing, feel free to:
- Open a [GitHub Discussion](https://github.com/yourusername/rake/discussions)
- Reach out to maintainers via [email](mailto:maintainers@example.com)

Thank you for contributing to Rake! 🚀
