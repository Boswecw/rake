# Rake V1 - Automated Data Ingestion Pipeline

<p align="center">
  <img src="Rake.png" alt="Rake Logo" width="600"/>
</p>

**Automated data ingestion pipeline for the Forge Ecosystem**

Rake is a production-ready SaaS backend that fetches documents from multiple sources, processes them through a 5-stage pipeline, and stores embeddings in DataForge for semantic search.

**Last Updated:** December 11, 2025
**System Status:** ✅ HEALTHY (100% Operational - All 4 Forge services running)

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-green.svg)](https://fastapi.tiangolo.com/)
[![SQLite/PostgreSQL](https://img.shields.io/badge/Database-SQLite%2FPostgreSQL-blue.svg)](https://www.sqlite.org/)
[![Test Coverage](https://img.shields.io/badge/coverage-80%25+-brightgreen.svg)](docs/TESTING.md)
[![Production Ready](https://img.shields.io/badge/status-production%20ready-success.svg)](docs/archive/IMPLEMENTATION_COMPLETE.md)

---

## 📚 Table of Contents

- [Overview](#-overview)
- [Ecosystem Integration](#-ecosystem-integration)
- [Quick Start](#-quick-start)
- [Architecture](#%EF%B8%8F-architecture)
- [Data Sources](#-data-sources)
  - [File Uploads](#file-uploads)
  - [SEC EDGAR](#-sec-edgar-integration)
  - [URL Scraping](#-url-scraping-integration)
  - [API Integration](#-api-integration)
  - [Database Queries](#%EF%B8%8F-database-queries)
- [API Endpoints](#-api-endpoints)
- [Database Setup](#%EF%B8%8F-database-setup--configuration)
- [Pipeline Details](#-pipeline-details)
- [Testing](#-testing)
- [Deployment](#-deployment)
  - [Docker](#-docker-deployment)
  - [CI/CD](#cicd-pipeline)
- [Documentation](#-documentation)
- [Contributing](#-contributing)
- [Support](#-support)

---

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
- ✅ **Database Queries**: Direct SQL database ingestion (PostgreSQL, MySQL, SQLite)

---

## 🌐 Ecosystem Integration

**Rake is part of the complete Forge Ecosystem with all 4 services operational (as of December 11, 2025):**

| Service | Port | Status | Purpose |
|---------|------|--------|---------|
| **DataForge** | 8788 | ✅ HEALTHY | Vector search & embeddings |
| **NeuroForge** | 8000 | ✅ HEALTHY | Multi-model AI routing (5 models) |
| **ForgeAgents** | 8787 | ✅ HEALTHY | AI agents & skills (120 skills) |
| **Rake** | 8002 | ✅ HEALTHY | Data ingestion pipeline (this service) |

**System Grade:** A (100% functional) - All services operational after December 11, 2025 bug fixes

### Quick Links to Ecosystem Documentation

- **[Quick Start Guide](../QUICK_START_GUIDE.md)** - Complete API reference & get all services running
- **[Next Steps & Roadmap](../NEXT_STEPS.md)** - Production deployment guide
- **[Quick Reference](../QUICK_REFERENCE.md)** - Command cheatsheet for all services
- **[Ecosystem Architecture](../docs/architecture/FORGE_UNIFIED_ARCHITECTURE.md)** - Complete system design
- **[Latest Session Report](../docs/sessions/SESSION_DEC_11_2025_COMPLETE.md)** - Dec 11 bug fixes (100% operational)
- **[Organized Documentation](../docs/README.md)** - Complete documentation index

---

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

### RAG Pipeline Features (NEW - Dec 2025)
- ✅ **Semantic Chunking**: Topic-aware text splitting with three strategies
  - **TOKEN_BASED**: Pure token-based splitting (fast)
  - **SEMANTIC**: Topic-aware splitting using embeddings (highest quality)
  - **HYBRID**: Balances semantic coherence with token limits (recommended)
- ✅ **Accurate Token Counting**: Uses `tiktoken` for exact GPT-4/Claude token counts
- ✅ **Semantic Boundary Detection**: Sentence embeddings with cosine similarity
- ✅ **Configurable Similarity Threshold**: Default 0.5 (empirically optimal)
- ✅ **Backward Compatible**: Graceful fallback to legacy chunking

**Expected Impact:** +30% improvement in chunk coherence

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
- SQLite (dev) or PostgreSQL 14+ (production)
- OpenAI API key
- DataForge service running (port 8788)

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

   **For Development (SQLite - Recommended):**
   ```bash
   # Database will be created automatically as SQLite file
   # No additional setup required!
   ```

   **For Production (PostgreSQL):**
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

# Database (SQLite for development)
DATABASE_URL=sqlite+aiosqlite:///./rake_jobs.db

# Database (PostgreSQL for production)
# DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/forge

# DataForge
DATAFORGE_BASE_URL=http://localhost:8788

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

## 🗄️ Database Queries

Rake supports direct ingestion from SQL databases with built-in security features, connection pooling, and flexible column mapping.

### Supported Databases

- **PostgreSQL**: Production-grade with full query timeout support
- **MySQL**: Wide compatibility for web applications
- **SQLite**: File-based for development and embedded use

### Security Features

- **Read-Only Mode**: Only SELECT queries allowed by default (prevents accidental modifications)
- **Query Validation**: Automatically blocks dangerous keywords (DROP, DELETE, INSERT, UPDATE, TRUNCATE, ALTER)
- **Parameterized Queries**: SQL injection prevention via parameter binding
- **Connection Pooling**: Efficient resource management with automatic cleanup
- **Query Timeouts**: Prevent runaway queries with configurable limits
- **Password Masking**: Automatic password redaction in logs

### Quick Start

**1. Fetch from PostgreSQL:**
```bash
curl -X POST http://localhost:8002/api/v1/jobs \
  -H "Content-Type: application/json" \
  -d '{
    "source": "database_query",
    "tenant_id": "tenant-123",
    "connection_string": "postgresql://readonly:password@localhost:5432/mydb",
    "query": "SELECT id, title, content FROM articles WHERE published = true LIMIT 100",
    "db_content_column": "content",
    "db_title_column": "title",
    "db_id_column": "id"
  }'
```

**2. Fetch with parameterized query (SQL injection prevention):**
```bash
curl -X POST http://localhost:8002/api/v1/jobs \
  -H "Content-Type: application/json" \
  -d '{
    "source": "database_query",
    "tenant_id": "tenant-123",
    "connection_string": "mysql://user:pass@localhost:3306/support_db",
    "query": "SELECT ticket_id, subject, description FROM tickets WHERE status = :status AND priority >= :priority",
    "query_params": {
      "status": "open",
      "priority": 3
    },
    "db_content_column": "description",
    "db_title_column": "subject",
    "db_id_column": "ticket_id",
    "db_max_rows": 500
  }'
```

**3. Fetch from SQLite:**
```bash
curl -X POST http://localhost:8002/api/v1/jobs \
  -H "Content-Type: application/json" \
  -d '{
    "source": "database_query",
    "tenant_id": "tenant-123",
    "connection_string": "sqlite:///data/reviews.db",
    "query": "SELECT review_id, product_name, review_text FROM reviews WHERE rating >= 4 LIMIT 200",
    "db_content_column": "review_text",
    "db_title_column": "product_name",
    "db_id_column": "review_id"
  }'
```

### Features

- ✅ Multi-database support (PostgreSQL, MySQL, SQLite)
- ✅ Security-first design (read-only mode, query validation, SQL injection prevention)
- ✅ Connection pooling and caching for performance
- ✅ Parameterized queries with named parameters (`:param_name`)
- ✅ Flexible column mapping (configure content, title, ID columns)
- ✅ Query timeout enforcement (prevents runaway queries)
- ✅ Row limit protection (hard limit: 10,000 rows)
- ✅ Password masking in logs (automatic security)
- ✅ Full pipeline integration (CLEAN → CHUNK → EMBED → STORE)

**📚 Full Guide**: See [docs/DATABASE_QUERY_GUIDE.md](docs/DATABASE_QUERY_GUIDE.md) for complete documentation.

## 🗄️ Database Setup & Configuration

Rake V1 uses PostgreSQL for job persistence and multi-tenant data isolation. This section provides complete setup instructions for development and production environments.

### Prerequisites

- PostgreSQL 14+ (recommended: PostgreSQL 15 or 16)
- `asyncpg` driver (included in requirements.txt)
- Alembic for migrations (included in requirements.txt)

### Development Setup (SQLite)

For local development and testing, Rake supports SQLite:

```bash
# Set in .env
DATABASE_URL=sqlite+aiosqlite:///data/rake.db

# Or use in-memory (testing only)
DATABASE_URL=sqlite+aiosqlite:///:memory:
```

**Note**: SQLite is suitable for development and testing only. Use PostgreSQL for production deployments.

### Production Setup (PostgreSQL)

#### 1. Install PostgreSQL

**Ubuntu/Debian:**
```bash
# Add PostgreSQL repository
sudo apt update
sudo apt install -y postgresql-14 postgresql-contrib-14

# Start PostgreSQL service
sudo systemctl start postgresql
sudo systemctl enable postgresql
```

**macOS:**
```bash
# Using Homebrew
brew install postgresql@14
brew services start postgresql@14
```

**Docker:**
```bash
# Using official PostgreSQL image
docker run -d \
  --name rake-postgres \
  -e POSTGRES_USER=rake_user \
  -e POSTGRES_PASSWORD=your_secure_password \
  -e POSTGRES_DB=forge \
  -p 5432:5432 \
  -v rake_postgres_data:/var/lib/postgresql/data \
  postgres:14
```

#### 2. Create Database and User

```bash
# Connect to PostgreSQL as superuser
sudo -u postgres psql

# Create user
CREATE USER rake_user WITH PASSWORD 'your_secure_password';

# Create database
CREATE DATABASE forge OWNER rake_user;

# Grant privileges
GRANT ALL PRIVILEGES ON DATABASE forge TO rake_user;

# Connect to the new database
\c forge

# Grant schema privileges
GRANT ALL ON SCHEMA public TO rake_user;

# Exit psql
\q
```

**Security Best Practices:**
- Use strong passwords (min 32 characters)
- Rotate passwords regularly
- Use separate users for different environments
- Enable SSL/TLS for production connections
- Configure `pg_hba.conf` to restrict access by IP

#### 3. Configure Database Connection

Update your `.env` file:

```bash
# Development
DATABASE_URL=postgresql+asyncpg://rake_user:your_password@localhost:5432/forge

# Production (with SSL)
DATABASE_URL=postgresql+asyncpg://rake_user:your_password@db.example.com:5432/forge?ssl=require

# Connection Pool Settings
DATABASE_POOL_SIZE=10
DATABASE_MAX_OVERFLOW=20
```

**Connection String Format:**
```
postgresql+asyncpg://username:password@host:port/database?options
```

**Common Options:**
- `ssl=require` - Require SSL/TLS encryption
- `ssl=verify-full` - Verify SSL certificate
- `connect_timeout=10` - Connection timeout in seconds
- `server_settings={"application_name":"rake"}` - Set application name

#### 4. Run Database Migrations

Rake uses Alembic for database schema management:

```bash
# Check current migration status
alembic current

# View migration history
alembic history

# Upgrade to latest version
alembic upgrade head

# Downgrade one version (if needed)
alembic downgrade -1

# Create new migration (after model changes)
alembic revision --autogenerate -m "Add new column"
```

**Migration Files Location:** `alembic/versions/`

#### 5. Verify Database Setup

```bash
# Test database connection
python -c "
import asyncio
from services.database import DatabaseService

async def test():
    db = DatabaseService()
    await db.init()
    healthy = await db.health_check()
    print(f'Database healthy: {healthy}')
    await db.close()

asyncio.run(test())
"
```

Or use the health check endpoint:
```bash
curl http://localhost:8002/health | jq '.dependencies.database'
```

### Database Schema

#### Jobs Table

The `jobs` table stores all pipeline job metadata:

| Column | Type | Description |
|--------|------|-------------|
| `id` | INTEGER | Auto-incrementing primary key |
| `job_id` | VARCHAR(64) | Unique job identifier (indexed) |
| `correlation_id` | VARCHAR(64) | Distributed tracing ID (indexed) |
| `source` | VARCHAR(50) | Source type (indexed) |
| `status` | VARCHAR(20) | Job status enum (indexed) |
| `tenant_id` | VARCHAR(64) | Multi-tenant identifier (indexed) |
| `created_at` | TIMESTAMP | Job creation time (indexed) |
| `completed_at` | TIMESTAMP | Job completion time |
| `duration_ms` | FLOAT | Total duration in milliseconds |
| `documents_stored` | INTEGER | Number of documents stored |
| `chunks_created` | INTEGER | Number of chunks created |
| `embeddings_generated` | INTEGER | Number of embeddings generated |
| `error_message` | TEXT | Error message if failed |
| `stages_completed` | JSON | List of completed stage names |
| `source_params` | JSON | Source-specific parameters |

**Indexes:**
- `job_id` (unique) - Fast job lookup
- `correlation_id` - Distributed tracing
- `source` - Filter by source type
- `status` - Filter by status
- `tenant_id` - Multi-tenant isolation
- `created_at` - Time-based queries
- Composite: `(tenant_id, status)` - Tenant job queries
- Composite: `(tenant_id, created_at)` - Tenant time-series
- Composite: `(status, created_at)` - Status time-series

### Database Configuration Options

All database settings are configured via environment variables:

```bash
# Database Connection
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/forge

# Connection Pooling (PostgreSQL only)
DATABASE_POOL_SIZE=10        # Base pool size (min connections)
DATABASE_MAX_OVERFLOW=20     # Max overflow connections
                             # Total max connections = pool_size + max_overflow

# Environment
ENVIRONMENT=production       # Controls SQL echo (debug in development)
```

**Connection Pool Sizing Guidelines:**

- **Development**: `POOL_SIZE=5`, `MAX_OVERFLOW=10`
- **Production (low traffic)**: `POOL_SIZE=10`, `MAX_OVERFLOW=20`
- **Production (high traffic)**: `POOL_SIZE=20`, `MAX_OVERFLOW=40`
- **Production (very high traffic)**: `POOL_SIZE=50`, `MAX_OVERFLOW=50`

**Formula:** `connections = pool_size + max_overflow`

**PostgreSQL Configuration:**
```sql
-- Check current connection limit
SHOW max_connections;  -- Default: 100

-- Increase if needed (in postgresql.conf)
max_connections = 200

-- Monitor active connections
SELECT count(*) FROM pg_stat_activity WHERE datname = 'forge';
```

### Backup & Restore

#### Automated Backups

```bash
#!/bin/bash
# backup_database.sh

BACKUP_DIR="/var/backups/rake"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/forge_backup_$TIMESTAMP.sql.gz"

# Create backup
pg_dump -U rake_user -h localhost forge | gzip > $BACKUP_FILE

# Keep only last 30 days
find $BACKUP_DIR -name "forge_backup_*.sql.gz" -mtime +30 -delete

echo "Backup completed: $BACKUP_FILE"
```

**Schedule with cron:**
```bash
# Daily backup at 2 AM
0 2 * * * /path/to/backup_database.sh
```

#### Manual Backup

```bash
# Full database backup
pg_dump -U rake_user -h localhost forge > backup.sql

# Compressed backup
pg_dump -U rake_user -h localhost forge | gzip > backup.sql.gz

# Schema only
pg_dump -U rake_user -h localhost --schema-only forge > schema.sql

# Data only
pg_dump -U rake_user -h localhost --data-only forge > data.sql
```

#### Restore Database

```bash
# Restore from backup
psql -U rake_user -h localhost forge < backup.sql

# Restore from compressed backup
gunzip -c backup.sql.gz | psql -U rake_user -h localhost forge

# Restore to new database
createdb -U rake_user new_forge
psql -U rake_user -h localhost new_forge < backup.sql
```

### Troubleshooting

#### Connection Issues

**Error: `FATAL: password authentication failed`**
```bash
# Check PostgreSQL is running
sudo systemctl status postgresql

# Verify user exists
sudo -u postgres psql -c "\du"

# Reset password
sudo -u postgres psql -c "ALTER USER rake_user WITH PASSWORD 'new_password';"

# Update DATABASE_URL in .env
```

**Error: `could not connect to server: Connection refused`**
```bash
# Check PostgreSQL is listening
sudo netstat -plnt | grep 5432

# Edit postgresql.conf
listen_addresses = '*'  # Or specific IP

# Edit pg_hba.conf (allow connections)
host    all             all             0.0.0.0/0               md5

# Restart PostgreSQL
sudo systemctl restart postgresql
```

**Error: `remaining connection slots are reserved`**
```bash
# Increase max_connections in postgresql.conf
max_connections = 200

# Or reduce POOL_SIZE + MAX_OVERFLOW in .env
```

#### Migration Issues

**Error: `Target database is not up to date`**
```bash
# Check current version
alembic current

# Upgrade to latest
alembic upgrade head
```

**Error: `Can't locate revision identified by`**
```bash
# Reset alembic version (WARNING: Only in development!)
alembic stamp head

# Or start fresh
alembic downgrade base
alembic upgrade head
```

#### Performance Issues

**Slow Queries:**
```sql
-- Enable query logging (postgresql.conf)
log_min_duration_statement = 1000  -- Log queries > 1 second

-- Check slow queries
SELECT pid, now() - query_start as duration, query
FROM pg_stat_activity
WHERE state = 'active' AND now() - query_start > interval '5 seconds';
```

**Missing Indexes:**
```sql
-- Check table size
SELECT pg_size_pretty(pg_total_relation_size('jobs'));

-- Analyze query performance
EXPLAIN ANALYZE SELECT * FROM jobs WHERE tenant_id = 'tenant-123';

-- Create index if needed
CREATE INDEX idx_custom ON jobs(your_column);
```

**Connection Pool Exhaustion:**
```bash
# Monitor pool usage
SELECT count(*) as active_connections
FROM pg_stat_activity
WHERE datname = 'forge' AND state = 'active';

# Increase pool size in .env
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=30
```

### Production Checklist

- [ ] PostgreSQL 14+ installed and running
- [ ] Database user created with strong password
- [ ] Database created with correct owner
- [ ] `DATABASE_URL` configured in `.env`
- [ ] Connection pool sizing configured
- [ ] SSL/TLS enabled for remote connections
- [ ] `pg_hba.conf` configured for secure access
- [ ] Database migrations applied (`alembic upgrade head`)
- [ ] Health check passing (`/health` endpoint)
- [ ] Automated backups configured
- [ ] Backup restoration tested
- [ ] Monitoring and alerting set up
- [ ] Connection pooling tuned for workload
- [ ] Query performance optimized
- [ ] Indexes verified with `EXPLAIN ANALYZE`

### Additional Resources

- [PostgreSQL Documentation](https://www.postgresql.org/docs/14/)
- [SQLAlchemy 2.0 Documentation](https://docs.sqlalchemy.org/en/20/)
- [Alembic Documentation](https://alembic.sqlalchemy.org/)
- [asyncpg Documentation](https://magicstack.github.io/asyncpg/)

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
Splits documents into semantic segments with three strategies:
- **TOKEN_BASED**: Fast token-based splitting
- **SEMANTIC**: Topic-aware splitting using sentence embeddings
- **HYBRID** (recommended): Balances semantic coherence with token limits
- Accurate token counting with `tiktoken` (exact GPT-4/Claude counts)
- Semantic boundary detection using cosine similarity
- Configurable overlap and chunk size
- Preserves context and respects sentence boundaries

**Configuration:**
```python
{
  "strategy": "hybrid",          # or "token", "semantic"
  "chunk_size": 500,
  "overlap": 50,
  "similarity_threshold": 0.5    # Semantic boundary threshold
}
```

**Performance:**
- +30% better chunk coherence (semantic strategies)
- 200ms - 3s processing time (depends on document size)

**See:** [RAG_PIPELINE_REFACTORING_COMPLETE.md](../RAG_PIPELINE_REFACTORING_COMPLETE.md) for technical details.

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

### Getting Started
- 📖 **[Quick Start Guide](QUICKSTART.md)** - Get up and running in 5 minutes
- 🏗️ **[Architecture Overview](docs/ARCHITECTURE.md)** - System design and components
- 🤝 **[Contributing Guide](CONTRIBUTING.md)** - Development guidelines and best practices

### API Documentation
- 🌐 **[Interactive API Docs](http://localhost:8002/api/docs)** - Swagger UI (when running)
- 📘 **[ReDoc](http://localhost:8002/api/redoc)** - Alternative API documentation (when running)

### Data Source Guides
- 📊 **[SEC EDGAR Guide](docs/SEC_EDGAR_GUIDE.md)** - Financial filings integration
- 🌐 **[URL Scraping Guide](docs/URL_SCRAPE_GUIDE.md)** - Web content extraction
- 🔌 **[API Integration Guide](docs/API_FETCH_GUIDE.md)** - External API ingestion
- 🗄️ **[Database Query Guide](docs/DATABASE_QUERY_GUIDE.md)** - Direct database ingestion

### Development & Testing
- 🧪 **[Testing Guide](docs/TESTING.md)** - Comprehensive test documentation (77/77 passing)
- 🗄️ **[Database Setup](#%EF%B8%8F-database-setup--configuration)** - PostgreSQL & SQLite configuration
- 🐛 **[Debugging](#-debugging)** - Troubleshooting and correlation IDs

### Deployment
- 🐳 **[Docker Deployment](#-docker-deployment)** - Containerization guide
- 🔄 **[CI/CD Pipeline](#cicd-pipeline)** - Automated testing & deployment

### Implementation History (Archive)
- 📋 **[Implementation Complete](docs/archive/IMPLEMENTATION_COMPLETE.md)** - Full implementation summary
- 📊 **[Technical Due Diligence](docs/archive/TECHNICAL_DUE_DILIGENCE_REPORT.md)** - Technical audit report
- 🐳 **[Docker & CI/CD Complete](docs/archive/DOCKER_CICD_COMPLETE.md)** - Containerization completion
- 📝 **[Feature Implementation Reports](docs/archive/)** - Detailed feature completion docs

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for:

- Development setup and workflow
- Coding standards and best practices
- Testing requirements (80%+ coverage)
- Pull request process
- Code of conduct

### Quick Development Setup

```bash
# 1. Fork and clone
git clone https://github.com/yourusername/rake.git
cd rake

# 2. Set up environment
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 3. Run tests
pytest --cov

# 4. Make changes and submit PR
git checkout -b feature/your-feature
# Make changes...
git commit -m "feat: add your feature"
git push origin feature/your-feature
```

## 📄 License

Part of the Forge Ecosystem - Internal Use

## 🆘 Support

For issues and questions:
- Check logs with correlation ID
- Review telemetry events
- Consult health check endpoint
- Check DataForge connectivity
- **Ecosystem Docs:** [../docs/README.md](../docs/README.md) - Complete documentation index
- **Quick Start All Services:** [../QUICK_START_GUIDE.md](../QUICK_START_GUIDE.md)
- **Latest Status:** [../docs/sessions/SESSION_DEC_11_2025_COMPLETE.md](../docs/sessions/SESSION_DEC_11_2025_COMPLETE.md)

---

## ✅ Project Status

**Current Version**: 1.0.0

### Completed Features
- ✅ **Core Pipeline**: 5-stage ingestion (FETCH → CLEAN → CHUNK → EMBED → STORE)
- ✅ **File Upload Support**: PDF, DOCX, TXT, PPTX, Markdown
- ✅ **SEC EDGAR Integration**: Financial filings (10-K, 10-Q, 8-K, etc.)
- ✅ **URL Scraping Integration**: Web pages with intelligent content extraction
- ✅ **API Integration**: External REST/HTTP APIs with multiple auth methods
- ✅ **Database Queries**: Direct SQL database ingestion (PostgreSQL, MySQL, SQLite)
- ✅ **Multi-tenant Support**: JWT authentication & tenant context
- ✅ **Job Scheduling**: APScheduler with cron/interval support
- ✅ **Retry Logic**: Exponential backoff for resilience
- ✅ **Telemetry**: Comprehensive event emission
- ✅ **Docker Support**: Production-ready containerization
- ✅ **CI/CD Pipeline**: Automated testing & deployment
- ✅ **Test Coverage**: 80%+ coverage with unit & integration tests
- ✅ **Type Safety**: 100% type hints with mypy validation
- ✅ **Documentation**: Complete API & implementation docs

### Statistics
- **Total Lines**: ~15,800+ lines of production code (added 600+ for semantic chunking)
- **Test Coverage**: 80%+
- **API Endpoints**: 6 REST endpoints
- **Data Sources**: 5 (File Upload, SEC EDGAR, URL Scraping, API Integration, Database Queries)
- **Pipeline Stages**: 5 (enhanced with semantic chunking)
- **Chunking Strategies**: 3 (TOKEN_BASED, SEMANTIC, HYBRID)
- **Documentation Files**: 18+ (includes RAG pipeline docs)

**Status**: 🚀 Production Ready
