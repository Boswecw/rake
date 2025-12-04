# Rake V1 - Quick Start Guide

**5-minute setup guide for Rake data ingestion pipeline**

---

## Prerequisites

- Python 3.11+
- PostgreSQL 14+ with pgvector
- OpenAI API key

---

## Installation

```bash
# 1. Navigate to rake directory
cd /home/charles/projects/Coding2025/Forge/rake

# 2. Create virtual environment
python3.11 -m venv venv
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt
```

---

## Configuration

```bash
# .env file already created - update these values:

# Critical settings:
OPENAI_API_KEY=sk-your-actual-key-here
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/forge
DATAFORGE_BASE_URL=http://localhost:8001

# Optional (has defaults):
ENVIRONMENT=development
LOG_LEVEL=INFO
MAX_WORKERS=4
CHUNK_SIZE=500
```

---

## Run the Service

```bash
# Development (with auto-reload)
python main.py

# Production
uvicorn main:app --host 0.0.0.0 --port 8002 --workers 4
```

Service will start on **http://localhost:8002**

---

## Test the API

### Health Check

```bash
curl http://localhost:8002/health
```

Expected response:
```json
{
  "status": "healthy",
  "service": "rake",
  "version": "1.0.0"
}
```

### Submit a Job

```bash
curl -X POST http://localhost:8002/api/v1/jobs \
  -H "Content-Type: application/json" \
  -d '{
    "source": "file_upload",
    "file_path": "/path/to/document.pdf",
    "tenant_id": "tenant-123"
  }'
```

Response:
```json
{
  "job_id": "job-abc123",
  "status": "pending",
  "correlation_id": "uuid-xyz"
}
```

### Check Job Status

```bash
curl http://localhost:8002/api/v1/jobs/job-abc123
```

### List All Jobs

```bash
curl http://localhost:8002/api/v1/jobs?page=1&page_size=10
```

---

## Run Tests

```bash
# All tests
pytest

# With coverage
pytest --cov=. --cov-report=html

# Unit tests only (fast)
pytest -m unit

# Integration tests
pytest -m integration
```

---

## API Documentation

**Interactive docs:** http://localhost:8002/api/docs
**ReDoc:** http://localhost:8002/api/redoc

---

## Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Service health check |
| GET | `/` | Service information |
| POST | `/api/v1/jobs` | Submit new job |
| GET | `/api/v1/jobs/{id}` | Get job status |
| GET | `/api/v1/jobs` | List jobs (paginated) |
| DELETE | `/api/v1/jobs/{id}` | Cancel job |

---

## 5-Stage Pipeline

```
1. FETCH  → Retrieve documents from sources
2. CLEAN  → Normalize and clean text
3. CHUNK  → Split into semantic segments
4. EMBED  → Generate vector embeddings (OpenAI)
5. STORE  → Persist to DataForge (PostgreSQL)
```

---

## Project Structure

```
rake/
├── main.py              # FastAPI entry point
├── config.py            # Configuration
├── scheduler.py         # Job scheduling
│
├── api/                 # REST API
│   └── routes.py
│
├── auth/                # Authentication
│   ├── jwt_handler.py
│   └── tenant_context.py
│
├── pipeline/            # 5-stage pipeline
│   ├── orchestrator.py
│   ├── fetch.py
│   ├── clean.py
│   ├── chunk.py
│   ├── embed.py
│   └── store.py
│
├── services/            # External services
│   ├── telemetry_client.py
│   ├── dataforge_client.py
│   └── embedding_service.py
│
├── sources/             # Data source adapters
│   ├── base.py
│   └── file_upload.py
│
├── models/              # Pydantic models
│   ├── document.py
│   └── events.py
│
├── utils/               # Utilities
│   ├── retry.py
│   └── text_processing.py
│
└── tests/               # Test suite
    ├── conftest.py
    ├── unit/
    └── integration/
```

---

## Common Tasks

### Enable Scheduler

```bash
# In .env
SCHEDULER_ENABLED=true
SCHEDULER_INTERVAL=3600  # seconds

# Add jobs via API or programmatically
```

### Add Authentication

```python
from fastapi import Depends
from auth import get_current_tenant

@app.get("/protected")
async def protected_route(tenant_id: str = Depends(get_current_tenant)):
    return {"tenant_id": tenant_id}
```

### View Logs

```bash
# Logs include correlation IDs
tail -f logs/rake.log | grep correlation_id
```

---

## Troubleshooting

### "Module not found" errors

```bash
# Ensure you're in the rake directory
cd /path/to/rake
python main.py
```

### Database connection errors

```bash
# Check PostgreSQL is running
pg_isready -h localhost -p 5432

# Test connection
psql -h localhost -U user -d forge
```

### OpenAI API errors

```bash
# Verify API key is set
echo $OPENAI_API_KEY

# Test key
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer $OPENAI_API_KEY"
```

---

## Environment Shortcuts

```bash
# Start service
rake-start() {
  cd /path/to/rake && source venv/bin/activate && python main.py
}

# Run tests
rake-test() {
  cd /path/to/rake && source venv/bin/activate && pytest
}

# Tail logs
rake-logs() {
  tail -f /path/to/logs/rake.log
}
```

---

## Production Deployment

```bash
# 1. Set production environment
ENVIRONMENT=production

# 2. Use production database
DATABASE_URL=postgresql+asyncpg://prod_user:pass@prod-db:5432/forge

# 3. Run with Gunicorn
gunicorn main:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8002 \
  --access-logfile - \
  --error-logfile -

# 4. Or use Docker (TODO)
docker build -t rake:latest .
docker run -p 8002:8002 --env-file .env rake:latest
```

---

## Key Features

✅ **5-stage pipeline** (FETCH → CLEAN → CHUNK → EMBED → STORE)
✅ **RESTful API** (6 endpoints)
✅ **Multi-tenant support** (JWT + tenant context)
✅ **Job scheduling** (APScheduler, cron/interval)
✅ **Retry logic** (exponential backoff, 3 attempts)
✅ **Telemetry** (comprehensive event emission)
✅ **Type safety** (100% type hints)
✅ **Documentation** (Google-style docstrings)
✅ **Testing** (pytest + fixtures)

---

## Support

**Documentation:**
- [README.md](README.md) - Full documentation
- [IMPLEMENTATION_COMPLETE.md](IMPLEMENTATION_COMPLETE.md) - Implementation details
- [tests/README.md](tests/README.md) - Testing guide

**Interactive Docs:**
- http://localhost:8002/api/docs

**Logs:**
- Stdout (development)
- Correlation IDs for tracing

---

**Ready to ingest data! 🚀**
