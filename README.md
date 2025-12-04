# Rake V1 - Automated Data Ingestion Pipeline

**Automated data ingestion pipeline for the Forge Ecosystem**

Rake is a production-ready SaaS backend that fetches documents from multiple sources, processes them through a 5-stage pipeline, and stores embeddings in DataForge for semantic search.

## 🎯 Overview

Rake handles the complete data ingestion workflow:

1. **FETCH** → Retrieve documents from sources (PDFs, APIs, websites)
2. **CLEAN** → Normalize and clean text content
3. **CHUNK** → Split documents into semantic segments
4. **EMBED** → Generate vector embeddings (OpenAI)
5. **STORE** → Persist to DataForge (PostgreSQL + pgvector)

## 🏗️ Architecture

```
┌─────────────┐
│   Sources   │ (PDF, API, Web)
└──────┬──────┘
       │
       ▼
┌─────────────┐
│   FETCH     │ Stage 1: Document Retrieval
└──────┬──────┘
       │
       ▼
┌─────────────┐
│   CLEAN     │ Stage 2: Text Normalization
└──────┬──────┘
       │
       ▼
┌─────────────┐
│   CHUNK     │ Stage 3: Semantic Chunking
└──────┬──────┘
       │
       ▼
┌─────────────┐
│   EMBED     │ Stage 4: Vector Generation
└──────┬──────┘
       │
       ▼
┌─────────────┐
│   STORE     │ Stage 5: DataForge Persistence
└─────────────┘
```

## 📦 Tech Stack

- **Python 3.11+** - Modern async Python
- **FastAPI** - High-performance API framework
- **Pydantic v2** - Data validation and settings
- **SQLAlchemy 2.0** - Async database ORM
- **PostgreSQL + pgvector** - Vector storage
- **OpenAI API** - Embedding generation
- **APScheduler** - Job scheduling

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- PostgreSQL 14+ with pgvector extension
- OpenAI API key
- DataForge service running (port 8001)

### Installation

1. **Clone and navigate to Rake:**
   ```bash
   cd /home/charles/projects/Coding2025/Forge/rake
   ```

2. **Create virtual environment:**
   ```bash
   python3.11 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment:**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

5. **Setup database:**
   ```bash
   # Create database
   createdb forge

   # Run migrations
   alembic upgrade head
   ```

6. **Run the service:**
   ```bash
   # Development
   python main.py

   # Or with uvicorn
   uvicorn main:app --reload
   ```

## 🔧 Configuration

All configuration is managed through environment variables. See [.env.example](.env.example) for all options.

### Key Settings

```bash
# Service
RAKE_PORT=8002
ENVIRONMENT=development

# Database
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/forge

# DataForge
DATAFORGE_BASE_URL=http://localhost:8001

# OpenAI
OPENAI_API_KEY=sk-...
OPENAI_EMBEDDING_MODEL=text-embedding-3-small

# Pipeline
MAX_WORKERS=4
CHUNK_SIZE=500
CHUNK_OVERLAP=50
```

## 📁 Project Structure

```
rake/
├── main.py                    # FastAPI entry point
├── config.py                  # Configuration management
├── scheduler.py               # Job scheduling
├── requirements.txt           # Dependencies
├── .env.example              # Environment template
│
├── api/                      # API layer
│   ├── routes.py             # REST endpoints
│   └── dependencies.py       # FastAPI dependencies
│
├── auth/                     # Authentication
│   ├── jwt_handler.py        # JWT utilities
│   └── tenant_context.py     # Multi-tenancy
│
├── sources/                  # Data source adapters
│   ├── base.py               # Abstract base class
│   └── file_upload.py        # PDF/document processing
│
├── pipeline/                 # 5-stage pipeline
│   ├── orchestrator.py       # Pipeline coordination
│   ├── fetch.py              # Stage 1: Fetch
│   ├── clean.py              # Stage 2: Clean
│   ├── chunk.py              # Stage 3: Chunk
│   ├── embed.py              # Stage 4: Embed
│   └── store.py              # Stage 5: Store
│
├── services/                 # External services
│   ├── dataforge_client.py   # DataForge API client
│   ├── embedding_service.py  # OpenAI embeddings
│   └── telemetry_client.py   # Telemetry events
│
├── models/                   # Pydantic models
│   ├── document.py           # Document types
│   ├── job.py                # Job state
│   └── events.py             # Telemetry events
│
├── utils/                    # Utilities
│   ├── text_processing.py    # Text cleaning
│   └── retry.py              # Retry logic
│
└── tests/                    # Test suite
    ├── conftest.py           # Pytest fixtures
    ├── unit/                 # Unit tests
    └── integration/          # Integration tests
```

## 🔌 API Endpoints

### Health Check
```bash
GET /health
```
Returns service health status and dependency checks.

### Submit Job
```bash
POST /api/v1/jobs
{
  "source": "file_upload",
  "document_url": "https://example.com/doc.pdf",
  "tenant_id": "tenant-123"
}
```

### Get Job Status
```bash
GET /api/v1/jobs/{job_id}
```

### List Jobs
```bash
GET /api/v1/jobs?tenant_id=tenant-123&status=completed
```

## 📊 Telemetry

Rake emits comprehensive telemetry events for monitoring and debugging:

### Event Types

| Event | Trigger | Severity |
|-------|---------|----------|
| `job_started` | Pipeline begins | info |
| `phase_completed` | Stage completes | info |
| `job_completed` | Pipeline succeeds | info |
| `job_failed` | Pipeline fails | error |

### Event Schema

```json
{
  "service": "rake",
  "event_type": "job_started",
  "severity": "info",
  "correlation_id": "uuid-string",
  "metadata": {
    "job_id": "rake-timestamp-source",
    "source": "file_upload",
    "tenant_id": "tenant-123"
  },
  "metrics": {
    "duration_ms": 1500.0,
    "items_processed": 10
  }
}
```

## 🧪 Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=. --cov-report=html

# Run specific test file
pytest tests/unit/test_fetch.py -v

# Run integration tests
pytest tests/integration/ -v

# Run with markers
pytest -m "unit" -v
```

## 🔄 Pipeline Details

### Stage 1: FETCH
Retrieves documents from configured sources:
- File uploads (PDF, DOCX, TXT)
- URL scraping
- API integration
- Database queries

### Stage 2: CLEAN
Normalizes text content:
- Remove formatting artifacts
- Normalize whitespace
- Remove duplicate content
- Extract metadata

### Stage 3: CHUNK
Splits documents into semantic segments:
- Token-based chunking
- Respects sentence boundaries
- Configurable overlap
- Preserves context

### Stage 4: EMBED
Generates vector embeddings:
- OpenAI text-embedding-3-small
- Batch processing (100 chunks/request)
- Automatic retry on failure
- Cost tracking

### Stage 5: STORE
Persists to DataForge:
- PostgreSQL + pgvector
- Multi-tenant isolation
- Metadata indexing
- Full-text search support

## 🔐 Security

- **Multi-tenancy**: Row-Level Security (RLS) in PostgreSQL
- **Authentication**: JWT-based auth with tenant context
- **API Keys**: Secure storage of OpenAI/Anthropic keys
- **Input Validation**: Pydantic models for all inputs
- **Rate Limiting**: Configurable per tenant

## 📈 Performance

- **Concurrent Processing**: Async Python with configurable workers
- **Batch Embedding**: 100 chunks per OpenAI request
- **Connection Pooling**: SQLAlchemy async pool
- **Retry Logic**: Exponential backoff for transient failures
- **Resource Limits**: Configurable max workers and timeouts

## 🐛 Debugging

### Correlation IDs
Every request gets a unique correlation ID for distributed tracing:
```bash
curl -H "X-Correlation-ID: my-trace-id" http://localhost:8002/api/v1/jobs
```

### Log Levels
```bash
# Debug mode (verbose)
LOG_LEVEL=DEBUG python main.py

# Production (info only)
LOG_LEVEL=INFO uvicorn main:app
```

### Health Checks
```bash
# Check service health
curl http://localhost:8002/health

# Check dependencies
curl http://localhost:8002/health | jq '.dependencies'
```

## 📝 Development

### Code Style
```bash
# Format code
black .
isort .

# Lint
flake8 .
mypy .
```

### Pre-commit Hooks
```bash
# Install pre-commit
pip install pre-commit
pre-commit install

# Run manually
pre-commit run --all-files
```

## 🚢 Deployment

### Production Checklist

- [ ] Set `ENVIRONMENT=production`
- [ ] Configure database connection pooling
- [ ] Set appropriate `MAX_WORKERS`
- [ ] Configure CORS `ALLOWED_ORIGINS`
- [ ] Set up monitoring and alerting
- [ ] Configure log aggregation
- [ ] Set up database backups
- [ ] Review security settings

### Docker Deployment

```dockerfile
# Dockerfile (to be created)
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8002"]
```

```bash
# Build and run
docker build -t rake:latest .
docker run -p 8002:8002 --env-file .env rake:latest
```

## 🤝 Integration with Forge Ecosystem

Rake integrates with:

- **DataForge** (port 8001) - Vector storage and search
- **Command Central** - Admin dashboard and monitoring
- **AuthorForge** - Document generation
- **NeuroForge** - AI orchestration

## 📚 Documentation

- [API Documentation](http://localhost:8002/api/docs) - Interactive API docs
- [ReDoc](http://localhost:8002/api/redoc) - Alternative API docs
- [Architecture Guide](docs/architecture.md) - Detailed architecture
- [Development Guide](docs/development.md) - Development workflow

## 📄 License

Part of the Forge Ecosystem - Internal Use

## 🆘 Support

For issues and questions:
- Check logs with correlation ID
- Review telemetry events
- Consult health check endpoint
- Check DataForge connectivity

---

**Status**: ✅ Phase 1 Complete (Foundation)
**Next**: Phase 2 - Telemetry & Models
