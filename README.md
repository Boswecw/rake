# Rake V1 - Automated Data Ingestion Pipeline

**Automated data ingestion pipeline for the Forge Ecosystem**

Rake is a production-ready SaaS backend that fetches documents from multiple sources, processes them through a 5-stage pipeline, and stores embeddings in DataForge for semantic search.

## 🎯 Overview

Rake handles the complete data ingestion workflow:

1. **FETCH** → Retrieve documents from sources (PDFs, APIs, websites, SEC EDGAR)
2. **CLEAN** → Normalize and clean text content
3. **CHUNK** → Split documents into semantic segments
4. **EMBED** → Generate vector embeddings (OpenAI)
5. **STORE** → Persist to DataForge (PostgreSQL + pgvector)

### 📂 Supported Data Sources

- ✅ **File Uploads**: PDF, DOCX, TXT, PPTX, Markdown
- ✅ **SEC EDGAR**: Financial filings (10-K, 10-Q, 8-K, etc.)
- ✅ **URL Scraping**: Web pages, articles, and documentation
- ✅ **API Integration**: External REST/HTTP APIs with multiple auth methods
- ⏳ **Database Queries**: Direct database ingestion (coming soon)

## 🏗️ Architecture

```
┌─────────────────────────────────────┐
│           Data Sources              │
│  (PDF, DOCX, SEC EDGAR, Web, API)  │
└────────────────┬────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────┐
│   FETCH (Stage 1)                   │
│   Document Retrieval & Validation   │
└────────────────┬────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────┐
│   CLEAN (Stage 2)                   │
│   Text Normalization & Cleaning     │
└────────────────┬────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────┐
│   CHUNK (Stage 3)                   │
│   Semantic Chunking & Segmentation  │
└────────────────┬────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────┐
│   EMBED (Stage 4)                   │
│   Vector Generation (OpenAI)        │
└────────────────┬────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────┐
│   STORE (Stage 5)                   │
│   DataForge (PostgreSQL + pgvector) │
└─────────────────────────────────────┘
```

## 📦 Tech Stack

- **Python 3.11+** - Modern async Python
- **FastAPI** - High-performance API framework
- **Pydantic v2** - Data validation and settings
- **SQLAlchemy 2.0** - Async database ORM
- **PostgreSQL + pgvector** - Vector storage
- **OpenAI API** - Embedding generation
- **APScheduler** - Job scheduling
- **Docker** - Containerization & orchestration
- **GitHub Actions** - CI/CD automation

## ✨ Key Features

### Data Sources
- ✅ **File Uploads**: PDF, DOCX, TXT, PPTX, Markdown
- ✅ **SEC EDGAR**: Financial filings from 10,000+ companies
- ✅ **URL Scraping**: Web pages with intelligent content extraction
- 🔜 API Integration, Database Queries

### Pipeline & Processing
- ✅ **5-Stage Pipeline**: FETCH → CLEAN → CHUNK → EMBED → STORE
- ✅ **Async Processing**: High-performance concurrent operations
- ✅ **Retry Logic**: Exponential backoff for resilience
- ✅ **Rate Limiting**: SEC-compliant (10 req/s)

### Production Ready
- ✅ **Multi-tenant Support**: JWT authentication & tenant isolation
- ✅ **Job Scheduling**: Cron and interval-based automation
- ✅ **Telemetry**: Comprehensive event emission & monitoring
- ✅ **Docker & CI/CD**: Automated testing & deployment
- ✅ **Type Safety**: 100% type hints with validation
- ✅ **Test Coverage**: 80%+ with unit & integration tests

### Developer Experience
- ✅ **RESTful API**: 6 endpoints with OpenAPI documentation
- ✅ **Interactive Docs**: Swagger UI & ReDoc
- ✅ **Comprehensive Docs**: Setup, API, and implementation guides
- ✅ **Error Handling**: Detailed error messages & correlation IDs

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

# SEC EDGAR (for financial filings)
SEC_EDGAR_USER_AGENT="YourCompany/1.0 contact@yourcompany.com"
SEC_EDGAR_RATE_LIMIT=0.1  # 10 requests/second (SEC requirement)

# URL Scraping (for web pages)
URL_SCRAPE_USER_AGENT="Rake/1.0 (Data Ingestion Bot)"
URL_SCRAPE_RATE_LIMIT=1.0  # 1 second between requests
URL_SCRAPE_RESPECT_ROBOTS=true  # Honor robots.txt

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

**File Upload:**
```bash
POST /api/v1/jobs
{
  "source": "file_upload",
  "file_path": "/path/to/document.pdf",
  "tenant_id": "tenant-123"
}
```

**SEC EDGAR Financial Filings:**
```bash
POST /api/v1/jobs
{
  "source": "sec_edgar",
  "ticker": "AAPL",
  "form_type": "10-K",
  "count": 1,
  "tenant_id": "tenant-123"
}
```

**Response:**
```json
{
  "job_id": "job-abc123",
  "correlation_id": "uuid-xyz",
  "status": "pending",
  "source": "sec_edgar"
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

## 📈 SEC EDGAR Integration

Rake includes native support for fetching financial filings from the SEC EDGAR database.

### Supported Filing Types

- **10-K**: Annual reports
- **10-Q**: Quarterly reports
- **8-K**: Current reports (material events)
- **DEF 14A**: Proxy statements
- **S-1, S-3**: Registration statements
- **13F-HR**: Institutional investment reports
- And many more...

### Quick Start

**1. Configure User-Agent** (required by SEC):
```bash
# Add to .env
SEC_EDGAR_USER_AGENT="MyCompany/1.0 support@mycompany.com"
```

**2. Fetch Apple's latest 10-K:**
```bash
curl -X POST http://localhost:8002/api/v1/jobs \
  -H "Content-Type: application/json" \
  -d '{
    "source": "sec_edgar",
    "ticker": "AAPL",
    "form_type": "10-K",
    "count": 1
  }'
```

**3. Fetch Microsoft's quarterly reports:**
```bash
curl -X POST http://localhost:8002/api/v1/jobs \
  -H "Content-Type: application/json" \
  -d '{
    "source": "sec_edgar",
    "cik": "0000789019",
    "form_type": "10-Q",
    "count": 3
  }'
```

### Parameters

| Parameter | Required | Description | Example |
|-----------|----------|-------------|---------|
| `ticker` | Either ticker OR cik | Stock ticker symbol | "AAPL", "MSFT" |
| `cik` | Either ticker OR cik | Company CIK number | "0000320193" |
| `form_type` | No | Filing form type | "10-K", "10-Q" |
| `count` | No | Number of filings (1-10) | 1 (default) |

### Features

- ✅ Automatic ticker → CIK conversion
- ✅ SEC-compliant rate limiting (10 req/s)
- ✅ HTML parsing and text extraction
- ✅ Comprehensive metadata extraction
- ✅ Full pipeline integration (CLEAN → CHUNK → EMBED → STORE)

**📚 Full Guide**: See [docs/SEC_EDGAR_GUIDE.md](docs/SEC_EDGAR_GUIDE.md) for complete documentation.

## 🌐 URL Scraping Integration

Rake includes intelligent web scraping with content extraction, robots.txt compliance, and sitemap support.

### Supported Content Types

- **Articles & Blog Posts**: Automatic main content extraction
- **Documentation**: Technical docs and API references
- **News Sites**: News articles and press releases
- **Web Pages**: Marketing pages and landing pages

### Quick Start

**1. Scrape a single URL:**
```bash
curl -X POST http://localhost:8002/api/v1/jobs \
  -H "Content-Type: application/json" \
  -d '{
    "source": "url_scrape",
    "url": "https://example.com/article",
    "tenant_id": "tenant-123"
  }'
```

**2. Bulk scrape from sitemap:**
```bash
curl -X POST http://localhost:8002/api/v1/jobs \
  -H "Content-Type: application/json" \
  -d '{
    "source": "url_scrape",
    "sitemap_url": "https://example.com/sitemap.xml",
    "max_pages": 10,
    "tenant_id": "tenant-123"
  }'
```

### Parameters

| Parameter | Required | Description | Example |
|-----------|----------|-------------|---------|
| `url` | Either url OR sitemap_url | Single URL to scrape | "https://blog.example.com/post" |
| `sitemap_url` | Either url OR sitemap_url | XML sitemap for bulk scraping | "https://example.com/sitemap.xml" |
| `max_pages` | No | Max URLs from sitemap (1-100) | 10 (default) |

### Features

- ✅ Intelligent content extraction (article, main, semantic tags)
- ✅ Metadata extraction (title, description, author, Open Graph)
- ✅ Robots.txt compliance checking
- ✅ Per-domain rate limiting
- ✅ Sitemap support (XML sitemaps and sitemap indexes)
- ✅ Content size limits and timeout protection
- ✅ Full pipeline integration (CLEAN → CHUNK → EMBED → STORE)

**📚 Full Guide**: See [docs/URL_SCRAPE_GUIDE.md](docs/URL_SCRAPE_GUIDE.md) for complete documentation.

## 🔌 API Integration

Rake includes flexible API integration with support for multiple authentication methods, pagination strategies, and response formats.

### Supported Authentication

- **API Key**: Header or query parameter
- **Bearer Token**: JWT, OAuth tokens
- **Basic Auth**: Username/password
- **Custom Headers**: Flexible authentication
- **None**: Public APIs

### Quick Start

**1. Fetch from public API:**
```bash
curl -X POST http://localhost:8002/api/v1/jobs \
  -H "Content-Type: application/json" \
  -d '{
    "source": "api_fetch",
    "api_url": "https://api.example.com/articles",
    "response_format": "json",
    "tenant_id": "tenant-123"
  }'
```

**2. Fetch with API key authentication:**
```bash
curl -X POST http://localhost:8002/api/v1/jobs \
  -H "Content-Type: application/json" \
  -d '{
    "source": "api_fetch",
    "api_url": "https://api.example.com/protected/data",
    "auth_type": "api_key",
    "api_key": "your-api-key",
    "api_key_name": "X-API-Key",
    "auth_location": "header",
    "response_format": "json",
    "data_path": "data.items",
    "tenant_id": "tenant-123"
  }'
```

**3. Fetch with pagination:**
```bash
curl -X POST http://localhost:8002/api/v1/jobs \
  -H "Content-Type: application/json" \
  -d '{
    "source": "api_fetch",
    "api_url": "https://api.example.com/articles",
    "auth_type": "bearer",
    "bearer_token": "your-token",
    "response_format": "json",
    "pagination_type": "json_path",
    "next_page_path": "pagination.next",
    "max_api_pages": 5,
    "tenant_id": "tenant-123"
  }'
```

### Features

- ✅ Multiple authentication methods (API Key, Bearer, Basic, Custom)
- ✅ HTTP methods support (GET, POST, PUT, PATCH, DELETE)
- ✅ Pagination strategies (Link headers, JSON path, offset-based)
- ✅ Response formats (JSON with path navigation, XML parsing)
- ✅ Field mapping (configurable content and title fields)
- ✅ Rate limiting and retry logic
- ✅ Full pipeline integration (CLEAN → CHUNK → EMBED → STORE)

**📚 Full Guide**: See [docs/API_FETCH_GUIDE.md](docs/API_FETCH_GUIDE.md) for complete documentation.

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

### 🐳 Docker Deployment

Rake includes production-ready Docker configuration with multi-stage builds and security best practices.

#### Quick Start with Docker Compose

**1. Start all services (Rake + PostgreSQL + pgAdmin):**

```bash
# Set required environment variables
export OPENAI_API_KEY=sk-your-key-here

# Start services
docker-compose up -d

# View logs
docker-compose logs -f rake
```

**2. Access services:**
- Rake API: http://localhost:8002
- API Docs: http://localhost:8002/api/docs
- pgAdmin: http://localhost:5050 (admin@rake.local / admin)

**3. Stop services:**
```bash
docker-compose down
# Or with volume cleanup
docker-compose down -v
```

#### Build and Run with Docker Only

**1. Build the image:**
```bash
docker build -t rake:latest .
```

**2. Run container:**
```bash
docker run -d \
  --name rake \
  -p 8002:8002 \
  -e OPENAI_API_KEY=sk-your-key-here \
  -e DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/forge \
  -e DATAFORGE_BASE_URL=http://host.docker.internal:8001 \
  rake:latest
```

**3. Check logs:**
```bash
docker logs -f rake
```

#### Docker Compose Services

The `docker-compose.yml` includes:

- **rake**: Main application service
- **postgres**: PostgreSQL 14+ with pgvector extension
- **pgadmin**: Database administration UI (optional, use `--profile tools`)

```bash
# Start with pgAdmin
docker-compose --profile tools up -d
```

#### Production Deployment

**Using Docker Swarm:**
```bash
# Initialize swarm
docker swarm init

# Deploy stack
docker stack deploy -c docker-compose.yml rake-stack

# Check services
docker service ls
docker service logs rake-stack_rake
```

**Using Kubernetes:**
```bash
# Build and push to registry
docker build -t your-registry/rake:v1.0.0 .
docker push your-registry/rake:v1.0.0

# Deploy with kubectl
kubectl apply -f k8s/deployment.yml
kubectl apply -f k8s/service.yml
```

**Environment Variables in Docker:**

Create a `.env` file for docker-compose:
```bash
# .env file
OPENAI_API_KEY=sk-your-actual-key
DATABASE_URL=postgresql+asyncpg://rake_user:rake_dev_password@postgres:5432/forge
DATAFORGE_BASE_URL=http://host.docker.internal:8001
ENVIRONMENT=production
LOG_LEVEL=INFO
MAX_WORKERS=4
JWT_SECRET_KEY=your-secret-key-here
```

#### Docker Image Details

**Multi-stage build:**
- Stage 1: Builder - Compiles dependencies
- Stage 2: Runtime - Minimal production image

**Security features:**
- Non-root user (`rake` uid 1000)
- Minimal base image (python:3.11-slim)
- No unnecessary build tools in final image
- Health check configuration

**Image size:** ~250MB (optimized with multi-stage build)

#### Health Checks

Docker includes built-in health monitoring:
```bash
# Check container health
docker ps --format "table {{.Names}}\t{{.Status}}"

# Health check endpoint
curl http://localhost:8002/health
```

#### Volumes

Persistent data volumes:
- `rake_postgres_data`: PostgreSQL database
- `rake_logs`: Application logs
- `rake_pgadmin_data`: pgAdmin configuration

```bash
# List volumes
docker volume ls

# Backup database
docker exec rake-postgres pg_dump -U rake_user forge > backup.sql

# Restore database
docker exec -i rake-postgres psql -U rake_user forge < backup.sql
```

### CI/CD Pipeline

Rake includes GitHub Actions workflows for automated testing and deployment.

#### Workflows

**1. Main CI/CD Pipeline (`.github/workflows/ci-cd.yml`):**
- Linting and type checking (black, isort, flake8, mypy)
- Unit tests with coverage
- Integration tests with PostgreSQL
- Docker image build and push to GitHub Container Registry
- Security scanning with Trivy
- Automated deployment on version tags

**2. Quick Test Pipeline (`.github/workflows/quick-test.yml`):**
- Fast unit tests on every commit
- Quick validation before full CI/CD

#### Setup GitHub Actions

**1. Configure secrets:**

Go to Settings → Secrets and variables → Actions, add:
- `OPENAI_API_KEY`: Your OpenAI API key (for integration tests)

**2. Enable GitHub Container Registry:**

```bash
# Login to GHCR
echo $GITHUB_TOKEN | docker login ghcr.io -u USERNAME --password-stdin

# Images are automatically published to:
# ghcr.io/your-username/your-repo/rake:latest
# ghcr.io/your-username/your-repo/rake:v1.0.0
```

**3. Trigger deployment:**

```bash
# Create and push version tag
git tag v1.0.0
git push origin v1.0.0

# GitHub Actions will:
# 1. Run full test suite
# 2. Build Docker image
# 3. Push to GHCR
# 4. Deploy to production (if configured)
```

#### CI/CD Features

✅ Automated testing (unit + integration)
✅ Code quality checks (linting, type checking)
✅ Security vulnerability scanning
✅ Docker image optimization
✅ Automated deployment on tags
✅ Coverage reporting to Codecov

#### Manual Deployment

For manual production deployment:

```bash
# Pull latest image
docker pull ghcr.io/your-username/your-repo/rake:latest

# Stop old container
docker stop rake && docker rm rake

# Run new version
docker run -d \
  --name rake \
  -p 8002:8002 \
  --env-file .env \
  --restart unless-stopped \
  ghcr.io/your-username/your-repo/rake:latest
```

## 🤝 Integration with Forge Ecosystem

Rake integrates with:

- **DataForge** (port 8001) - Vector storage and search
- **Command Central** - Admin dashboard and monitoring
- **AuthorForge** - Document generation
- **NeuroForge** - AI orchestration

## 📚 Documentation

### API Documentation
- [Interactive API Docs](http://localhost:8002/api/docs) - Swagger UI
- [ReDoc](http://localhost:8002/api/redoc) - Alternative API documentation

### Feature Guides
- [SEC EDGAR Guide](docs/SEC_EDGAR_GUIDE.md) - Complete SEC EDGAR integration guide
- [URL Scraping Guide](docs/URL_SCRAPE_GUIDE.md) - Complete URL scraping integration guide
- [API Integration Guide](docs/API_FETCH_GUIDE.md) - Complete API integration guide
- [Quick Start Guide](QUICKSTART.md) - 5-minute setup guide
- [Testing Guide](tests/README.md) - Testing documentation

### Implementation Details
- [Implementation Complete](IMPLEMENTATION_COMPLETE.md) - Full implementation summary
- [Docker & CI/CD](DOCKER_CICD_COMPLETE.md) - Containerization guide
- [SEC EDGAR Implementation](SEC_EDGAR_IMPLEMENTATION_COMPLETE.md) - SEC integration details

## 📄 License

Part of the Forge Ecosystem - Internal Use

## 🆘 Support

For issues and questions:
- Check logs with correlation ID
- Review telemetry events
- Consult health check endpoint
- Check DataForge connectivity

---

## ✅ Project Status

**Current Version**: 1.0.0

### Completed Features
- ✅ **Core Pipeline**: 5-stage ingestion (FETCH → CLEAN → CHUNK → EMBED → STORE)
- ✅ **File Upload Support**: PDF, DOCX, TXT, PPTX, Markdown
- ✅ **SEC EDGAR Integration**: Financial filings (10-K, 10-Q, 8-K, etc.)
- ✅ **URL Scraping Integration**: Web pages with intelligent content extraction
- ✅ **API Integration**: External REST/HTTP APIs with multiple auth methods
- ✅ **Multi-tenant Support**: JWT authentication & tenant context
- ✅ **Job Scheduling**: APScheduler with cron/interval support
- ✅ **Retry Logic**: Exponential backoff for resilience
- ✅ **Telemetry**: Comprehensive event emission
- ✅ **Docker Support**: Production-ready containerization
- ✅ **CI/CD Pipeline**: Automated testing & deployment
- ✅ **Test Coverage**: 80%+ coverage with unit & integration tests
- ✅ **Type Safety**: 100% type hints with mypy validation
- ✅ **Documentation**: Complete API & implementation docs

### In Development
- ⏳ **Database Queries**: Direct database ingestion (planned)

### Statistics
- **Total Lines**: ~14,000+ lines of production code
- **Test Coverage**: 80%+
- **API Endpoints**: 6 REST endpoints
- **Data Sources**: 4 (File Upload, SEC EDGAR, URL Scraping, API Integration)
- **Pipeline Stages**: 5
- **Documentation Files**: 14+

**Status**: 🚀 Production Ready
