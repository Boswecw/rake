# Rake V1 - System Architecture

**Version:** 1.0
**Last Updated:** December 4, 2025
**Status:** Production Ready

---

## Table of Contents

- [System Overview](#system-overview)
- [Architecture Diagram](#architecture-diagram)
- [Core Components](#core-components)
- [Data Flow](#data-flow)
- [Pipeline Stages](#pipeline-stages)
- [Multi-Tenancy](#multi-tenancy)
- [Security](#security)
- [External Dependencies](#external-dependencies)
- [Scalability](#scalability)

---

## System Overview

Rake V1 is a production-grade data ingestion pipeline that transforms raw documents from multiple sources into searchable vector embeddings stored in DataForge (Qdrant). It supports 5 data sources and processes data through a robust 5-stage pipeline.

### Key Characteristics

- **Async-first**: Built with Python asyncio for high concurrency
- **Multi-tenant**: Tenant isolation at all layers
- **Resilient**: Retry logic, error handling, telemetry
- **Scalable**: Horizontal scaling via stateless design
- **Observable**: Comprehensive telemetry and logging

### Technology Stack

| Layer | Technology |
|-------|-----------|
| **Runtime** | Python 3.11+ |
| **Web Framework** | FastAPI 0.115+ |
| **Async Engine** | asyncio + aiohttp |
| **Database** | PostgreSQL 14+ (asyncpg) |
| **Vector Store** | Qdrant (via DataForge) |
| **LLM Provider** | OpenAI (text-embedding-3-small) |
| **Testing** | pytest + pytest-asyncio |

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                         Client Applications                      │
│                     (HTTP POST /api/v1/jobs)                     │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                         Rake API Layer                           │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │  Job Submit  │  │  Job Status  │  │    Health    │          │
│  │   Endpoint   │  │   Endpoint   │  │    Check     │          │
│  └──────┬───────┘  └──────┬───────┘  └──────────────┘          │
│         │                  │                                     │
│         │  ┌───────────────┴───────────────┐                    │
│         │  │  JWT Auth + Tenant Context    │                    │
│         │  └───────────────────────────────┘                    │
└─────────┼──────────────────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Pipeline Orchestrator                         │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  Manages 5-stage pipeline execution                      │   │
│  │  Tracks progress, handles errors, emits telemetry        │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────┬───────────────────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Pipeline Stages (Sequential)                │
│                                                                   │
│  1. FETCH  ───▶  2. CLEAN  ───▶  3. CHUNK  ───▶  4. EMBED       │
│                                                        │          │
│                                                        ▼          │
│                                                   5. STORE        │
│                                                        │          │
└────────────────────────────────────────────────────────┼─────────┘
                                                         │
                ┌────────────────────────────────────────┴──────────┐
                │                                                   │
                ▼                                                   ▼
┌──────────────────────────────┐               ┌──────────────────────────────┐
│     PostgreSQL Database      │               │       DataForge (Qdrant)     │
│  ┌────────────────────────┐  │               │  ┌────────────────────────┐  │
│  │   Jobs Table           │  │               │  │  Vector Embeddings     │  │
│  │  - Job metadata        │  │               │  │  - Searchable chunks   │  │
│  │  - Status tracking     │  │               │  │  - Multi-tenant        │  │
│  │  - Multi-tenant        │  │               │  └────────────────────────┘  │
│  └────────────────────────┘  │               └──────────────────────────────┘
└──────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                     External Services                            │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │   OpenAI    │  │  SEC EDGAR  │  │  External   │             │
│  │  Embeddings │  │    API      │  │  Databases  │             │
│  └─────────────┘  └─────────────┘  └─────────────┘             │
└─────────────────────────────────────────────────────────────────┘
```

---

## Core Components

### 1. API Layer (`api/`)

**Purpose**: HTTP interface for job submission and status queries

**Components**:
- `jobs.py` - Job management endpoints
- `health.py` - Health check endpoint

**Key Features**:
- JWT authentication with tenant context
- Async request handling
- Job submission (POST /api/v1/jobs)
- Job status queries (GET /api/v1/jobs/{job_id})
- Job listing with pagination

### 2. Pipeline Orchestrator (`pipeline/orchestrator.py`)

**Purpose**: Coordinates 5-stage pipeline execution

**Responsibilities**:
- Stage execution management
- Progress tracking
- Error handling and recovery
- Telemetry emission
- Job state persistence

**Execution Flow**:
```python
async def run(job_id, source, tenant_id, **params):
    # 1. Initialize job in database
    # 2. Execute FETCH stage
    # 3. Execute CLEAN stage
    # 4. Execute CHUNK stage
    # 5. Execute EMBED stage
    # 6. Execute STORE stage
    # 7. Update job status (completed/failed)
    # 8. Emit telemetry
    return job_results
```

### 3. Pipeline Stages (`pipeline/`)

#### Stage 1: FETCH (`fetch.py`)
Retrieves raw documents from 5 data sources:
- `file_upload` - Local file system
- `sec_edgar` - SEC EDGAR API
- `url_scrape` - Web scraping
- `api_fetch` - External REST APIs
- `database_query` - SQL databases

**Output**: List of `Document` objects with raw content

#### Stage 2: CLEAN (`clean.py`)
Normalizes and cleans text:
- HTML tag removal
- Whitespace normalization
- Special character handling
- Empty content filtering

**Output**: List of `Document` objects with cleaned content

#### Stage 3: CHUNK (`chunk.py`)
Splits documents into semantic chunks:
- Sliding window chunking
- Token counting (cl100k_base tokenizer)
- Overlap handling (default: 100 tokens)
- Chunk size limits (default: 500 tokens)

**Output**: List of `Chunk` objects

#### Stage 4: EMBED (`embed.py`)
Generates vector embeddings:
- OpenAI text-embedding-3-small (1536 dimensions)
- Batch processing (default: 100 chunks/batch)
- Retry logic with exponential backoff
- Cost tracking

**Output**: List of `Chunk` objects with embeddings

#### Stage 5: STORE (`store.py`)
Persists embeddings to DataForge:
- Tenant-isolated collections
- Metadata preservation
- Batch upsert operations
- Error recovery

**Output**: Storage confirmation with counts

### 4. Services (`services/`)

#### Database Service (`database.py`)
- Async PostgreSQL operations
- Job CRUD operations
- Multi-tenant filtering
- Connection pooling

#### Embedding Service (`embedding_service.py`)
- OpenAI API integration
- Batch embedding generation
- Token counting
- Cost calculation

#### DataForge Client (`dataforge_client.py`)
- Qdrant vector store integration
- Collection management
- Embedding storage
- Query interface

#### Telemetry Client (`telemetry_client.py`)
- Event emission
- Structured logging
- Performance tracking
- Error reporting

### 5. Authentication & Authorization (`auth/`)

#### JWT Handler (`jwt_handler.py`)
- Token creation and verification
- HS256 signing algorithm
- Configurable expiration
- Role-based access control (RBAC)

#### Tenant Context (`tenant_context.py`)
- Context variable management
- Request-scoped tenant isolation
- Dependency injection for FastAPI
- Multi-tenant query filtering

### 6. Models (`models/`)

#### Document Models (`document.py`)
- Pydantic V2 models
- Validation and serialization
- Type safety

**Key Models**:
- `Document` - Raw document
- `Chunk` - Text chunk with embedding
- `JobSubmission` - Job request
- `JobResponse` - Job status

#### Job Model (`job.py`)
- SQLAlchemy 2.0 ORM model
- Job persistence schema
- Status enum (PENDING, FETCHING, CLEANING, etc.)

### 7. Utilities (`utils/`)

- `retry.py` - Exponential backoff retry logic
- `text_processing.py` - Text normalization utilities
- `token_counter.py` - tiktoken integration

---

## Data Flow

### Job Submission Flow

```
1. Client submits job → POST /api/v1/jobs
   ↓
2. JWT authentication + tenant extraction
   ↓
3. Job created in database (status: PENDING)
   ↓
4. Orchestrator.run() executes stages sequentially
   ↓
5. Each stage:
   - Processes data
   - Updates job status
   - Emits telemetry
   - Handles errors
   ↓
6. Final status update (COMPLETED/FAILED)
   ↓
7. Return job results to client
```

### Data Transformation Flow

```
Raw Source Data (5 types)
   │
   ▼ FETCH
List[Document(content: str, metadata: dict)]
   │
   ▼ CLEAN
List[Document(content: cleaned_str, metadata: dict)]
   │
   ▼ CHUNK
List[Chunk(content: str, token_count: int, position: int)]
   │
   ▼ EMBED
List[Chunk(content: str, embedding: List[float])]
   │
   ▼ STORE
Qdrant Collection (tenant-specific, searchable)
```

---

## Pipeline Stages

### Stage Characteristics

| Stage | Avg Duration | Error Handling | Retry Logic | Telemetry |
|-------|-------------|----------------|-------------|-----------|
| FETCH | 1-10s | Source-specific | Yes (3 retries) | ✅ |
| CLEAN | 0.1-1s | Graceful fallback | No | ✅ |
| CHUNK | 0.5-2s | Validation errors | No | ✅ |
| EMBED | 2-30s | API rate limits | Yes (3 retries) | ✅ |
| STORE | 1-5s | Network errors | Yes (3 retries) | ✅ |

### Error Recovery

Each stage implements error handling:

```python
try:
    result = await stage_function(input_data)
    telemetry.emit_stage_completed(stage_name)
except RetryableError as e:
    # Retry with exponential backoff
    result = await retry_with_backoff(stage_function, input_data)
except FatalError as e:
    # Mark job as failed, emit error event
    telemetry.emit_stage_failed(stage_name, error=str(e))
    raise
```

---

## Multi-Tenancy

### Tenant Isolation Layers

**1. Authentication Layer**
- JWT tokens include `tenant_id` claim
- Tokens verified on every request
- Invalid tokens → 401 Unauthorized

**2. Context Layer**
- `tenant_context.py` manages context variable
- Tenant ID injected into all operations
- Request-scoped isolation

**3. Database Layer**
- `jobs` table has `tenant_id` column (indexed)
- All queries filter by tenant
- Composite indexes: `(tenant_id, status)`, `(tenant_id, created_at)`

**4. Vector Store Layer**
- DataForge creates tenant-specific collections
- Collection naming: `{tenant_id}_documents`
- Complete data isolation

### Example Tenant Flow

```python
# 1. Extract tenant from JWT
token_payload = verify_token(token)
tenant_id = token_payload["tenant_id"]

# 2. Set context
set_tenant_context(tenant_id)

# 3. Database auto-filters
jobs = await db.list_jobs()  # Automatically filters by tenant_id

# 4. DataForge uses tenant collection
await dataforge.store_embeddings(
    collection=f"{tenant_id}_documents",
    embeddings=chunks
)
```

---

## Security

### Authentication & Authorization

- **JWT Tokens**: HS256 algorithm, 60-minute expiration
- **Secret Key**: Minimum 32 characters (configured via env)
- **HTTPS Only**: Production deployments require TLS
- **CORS**: Configurable origins, credentials support

### Data Security

- **Password Masking**: Database passwords masked in logs
- **Tenant Isolation**: Complete data segregation
- **Input Validation**: Pydantic models validate all inputs
- **SQL Injection**: SQLAlchemy ORM prevents SQL injection

### Best Practices

1. Rotate `JWT_SECRET_KEY` regularly
2. Use strong passwords (32+ characters)
3. Enable SSL/TLS for PostgreSQL connections
4. Configure `pg_hba.conf` to restrict access by IP
5. Monitor failed authentication attempts

---

## External Dependencies

### Required Services

| Service | Purpose | Fallback |
|---------|---------|----------|
| **PostgreSQL 14+** | Job persistence | None (required) |
| **DataForge (Qdrant)** | Vector storage | None (required) |
| **OpenAI API** | Embeddings | None (required) |

### Optional Services

| Service | Purpose | Fallback |
|---------|---------|----------|
| **SEC EDGAR** | Financial data | Skip if unavailable |
| **External DBs** | Database queries | Skip if unavailable |
| **Web URLs** | URL scraping | Skip if unavailable |

### Dependency Health Checks

```bash
GET /health

Response:
{
  "status": "healthy",
  "dependencies": {
    "database": "healthy",
    "dataforge": "healthy",
    "openai": "healthy"
  }
}
```

---

## Scalability

### Horizontal Scaling

**Stateless Design**:
- No in-memory state (except connection pools)
- All job state persisted in PostgreSQL
- Multiple instances can run concurrently

**Load Balancing**:
```
┌──────────┐
│  Client  │
└────┬─────┘
     │
     ▼
┌─────────────┐
│ Load Balance│
└────┬────────┘
     │
     ├────────┬────────┬────────┐
     ▼        ▼        ▼        ▼
  ┌────┐  ┌────┐  ┌────┐  ┌────┐
  │Rake│  │Rake│  │Rake│  │Rake│
  │ 1  │  │ 2  │  │ 3  │  │ 4  │
  └────┘  └────┘  └────┘  └────┘
     │        │        │        │
     └────────┴────────┴────────┘
              │
              ▼
     ┌─────────────────┐
     │   PostgreSQL    │
     └─────────────────┘
```

### Vertical Scaling

**Configuration Options**:
```bash
# Increase worker threads
MAX_WORKERS=8

# Increase batch sizes
OPENAI_BATCH_SIZE=200
CHUNK_SIZE=1000

# Increase connection pool
DATABASE_POOL_SIZE=50
DATABASE_MAX_OVERFLOW=50
```

### Performance Optimization

**Database**:
- Connection pooling (default: 10+20)
- Composite indexes on frequent queries
- Query optimization with `EXPLAIN ANALYZE`

**Pipeline**:
- Batch processing (embeddings, storage)
- Async I/O for all network operations
- Parallel chunk processing (where applicable)

**Monitoring**:
- Telemetry events track duration
- Query performance logs
- Connection pool metrics

---

## Deployment Architecture

### Development

```
Developer Machine
├── SQLite (in-memory testing)
├── Local DataForge (Docker)
└── OpenAI API (cloud)
```

### Production

```
┌──────────────────────────────────────────────────────────────┐
│                        Cloud Provider                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │  Rake API    │  │  PostgreSQL  │  │   Qdrant     │       │
│  │  (3 replicas)│  │  (Primary +  │  │  (Cluster)   │       │
│  │              │  │   Replica)   │  │              │       │
│  └──────────────┘  └──────────────┘  └──────────────┘       │
│                                                               │
│  ┌──────────────────────────────────────────────────────┐    │
│  │            Monitoring & Observability                │    │
│  │  - Logs (structured JSON)                           │    │
│  │  - Metrics (telemetry events)                       │    │
│  │  - Alerts (failure thresholds)                      │    │
│  └──────────────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────────────┘
```

---

## Configuration

All configuration via environment variables:

```bash
# Application
ENVIRONMENT=production
LOG_LEVEL=INFO
MAX_WORKERS=4

# Database
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/forge
DATABASE_POOL_SIZE=10
DATABASE_MAX_OVERFLOW=20

# DataForge
DATAFORGE_BASE_URL=https://dataforge.example.com
DATAFORGE_API_KEY=your-api-key

# OpenAI
OPENAI_API_KEY=sk-your-key
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
OPENAI_BATCH_SIZE=100

# JWT Authentication
JWT_SECRET_KEY=your-secret-key-minimum-32-characters
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=60
```

---

## Future Enhancements

### Short-term (Q1 2026)

- [ ] Support for additional embedding models (Anthropic, Cohere)
- [ ] Asynchronous job processing (background workers)
- [ ] Enhanced retry strategies (circuit breaker pattern)
- [ ] Metrics dashboard (Grafana integration)

### Long-term (Q2-Q4 2026)

- [ ] Real-time job status updates (WebSockets)
- [ ] Advanced query capabilities (hybrid search)
- [ ] Multi-region deployment support
- [ ] GraphQL API option
- [ ] ML-based document classification

---

## Additional Resources

- [README.md](../README.md) - Main documentation
- [QUICKSTART.md](../QUICKSTART.md) - 5-minute setup guide
- [TESTING.md](TESTING.md) - Test suite documentation
- [CONTRIBUTING.md](../CONTRIBUTING.md) - Development guidelines
- [API_FETCH_GUIDE.md](API_FETCH_GUIDE.md) - API fetch source guide
- [SEC_EDGAR_GUIDE.md](SEC_EDGAR_GUIDE.md) - SEC EDGAR source guide
- [URL_SCRAPE_GUIDE.md](URL_SCRAPE_GUIDE.md) - URL scraping guide
- [DATABASE_QUERY_GUIDE.md](DATABASE_QUERY_GUIDE.md) - Database query guide
