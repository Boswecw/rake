# Rake V1 Implementation TODO

**Status codes:** BACKLOG → READY → DOING → REVIEW → BLOCKED → DONE
**Priority:** P0 critical, P1 high, P2 normal, P3 nice-to-have

---

## RAKE-001: main.py - FastAPI Entry Point
**Status:** READY
**Priority:** P0
**Owner:** Claude
**Area:** Foundation
**Files:** `rake/main.py`
**Deps:** None

### Acceptance:
- [ ] FastAPI application initialization
- [ ] CORS middleware configuration
- [ ] Correlation ID middleware
- [ ] Health check endpoint
- [ ] Startup/shutdown event handlers
- [ ] All type hints and docstrings
- [ ] Telemetry integration ready

**Notes:** Entry point for Rake service on port 8002.

---

## RAKE-002: config.py - Configuration Management
**Status:** READY
**Priority:** P0
**Owner:** Claude
**Area:** Foundation
**Files:** `rake/config.py`
**Deps:** None

### Acceptance:
- [ ] Pydantic Settings v2 configuration
- [ ] Environment variable loading
- [ ] Database URL validation
- [ ] Service URL validation
- [ ] API key validation
- [ ] Pipeline settings (workers, chunk size, etc.)

**Notes:** Centralized configuration using Pydantic BaseSettings.

---

## RAKE-003: requirements.txt - Dependencies
**Status:** READY
**Priority:** P0
**Owner:** Claude
**Area:** Foundation
**Files:** `rake/requirements.txt`
**Deps:** None

### Acceptance:
- [ ] FastAPI 0.104+
- [ ] Pydantic 2.5+
- [ ] SQLAlchemy 2.0+ (async)
- [ ] OpenAI SDK
- [ ] PDF processing libraries
- [ ] Testing dependencies

**Notes:** All dependencies with version pins.

---

## RAKE-004: .env.example - Environment Template
**Status:** READY
**Priority:** P0
**Owner:** Claude
**Area:** Foundation
**Files:** `rake/.env.example`
**Deps:** RAKE-002

### Acceptance:
- [ ] Database configuration
- [ ] Service URLs
- [ ] API keys (placeholder)
- [ ] Pipeline settings
- [ ] Comments for each variable

**Notes:** Template for production deployment.

---

## RAKE-005: services/telemetry_client.py - Telemetry Emission
**Status:** BACKLOG
**Priority:** P0
**Owner:** Claude
**Area:** Telemetry
**Files:** `rake/services/telemetry_client.py`
**Deps:** RAKE-001, RAKE-002

### Acceptance:
- [ ] TelemetryClient class with async methods
- [ ] emit_job_started()
- [ ] emit_phase_completed()
- [ ] emit_job_completed()
- [ ] emit_job_failed()
- [ ] Correlation ID tracking
- [ ] HTTP client for telemetry endpoint

**Notes:** Critical for observability across all pipeline stages.

---

## RAKE-006: models/document.py - Pydantic Models
**Status:** BACKLOG
**Priority:** P0
**Owner:** Claude
**Area:** Models
**Files:** `rake/models/document.py`, `rake/models/job.py`, `rake/models/events.py`
**Deps:** RAKE-002

### Acceptance:
- [ ] RawDocument model
- [ ] CleanedDocument model
- [ ] Chunk model
- [ ] Embedding model
- [ ] JobStatus model
- [ ] TelemetryEvent model
- [ ] All Pydantic v2 syntax

**Notes:** Core data models for pipeline stages.

---

## RAKE-007: sources/base.py - Abstract Source Adapter
**Status:** BACKLOG
**Priority:** P1
**Owner:** Claude
**Area:** Sources
**Files:** `rake/sources/base.py`
**Deps:** RAKE-006

### Acceptance:
- [ ] Abstract BaseSource class
- [ ] fetch() method signature
- [ ] validate() method signature
- [ ] Type hints and docstrings

**Notes:** Interface for all source adapters.

---

## RAKE-008: sources/file_upload.py - PDF Processing
**Status:** BACKLOG
**Priority:** P1
**Owner:** Claude
**Area:** Sources
**Files:** `rake/sources/file_upload.py`
**Deps:** RAKE-007

### Acceptance:
- [ ] FileUploadSource implementation
- [ ] PDF text extraction (pdfplumber)
- [ ] DOCX support
- [ ] TXT support
- [ ] Error handling for corrupted files
- [ ] Metadata extraction

**Notes:** Primary source adapter for V1.

---

## RAKE-009: pipeline/fetch.py - Stage 1: Fetch
**Status:** BACKLOG
**Priority:** P1
**Owner:** Claude
**Area:** Pipeline
**Files:** `rake/pipeline/fetch.py`
**Deps:** RAKE-007, RAKE-008

### Acceptance:
- [ ] fetch_stage() async function
- [ ] Source adapter routing
- [ ] Error handling and retries
- [ ] Telemetry emission
- [ ] Returns List[RawDocument]

**Notes:** First stage of 5-stage pipeline.

---

## RAKE-010: pipeline/clean.py - Stage 2: Clean
**Status:** BACKLOG
**Priority:** P1
**Owner:** Claude
**Area:** Pipeline
**Files:** `rake/pipeline/clean.py`
**Deps:** RAKE-006

### Acceptance:
- [ ] clean_stage() async function
- [ ] Text normalization
- [ ] Whitespace cleanup
- [ ] HTML tag removal
- [ ] Word count calculation
- [ ] Returns List[CleanedDocument]

**Notes:** Text cleaning and normalization.

---

## RAKE-011: pipeline/chunk.py - Stage 3: Chunk
**Status:** BACKLOG
**Priority:** P1
**Owner:** Claude
**Area:** Pipeline
**Files:** `rake/pipeline/chunk.py`
**Deps:** RAKE-006

### Acceptance:
- [ ] chunk_stage() async function
- [ ] Token-based chunking (tiktoken)
- [ ] Configurable chunk size and overlap
- [ ] Sentence boundary respect
- [ ] Returns List[Chunk]

**Notes:** Semantic chunking with overlap.

---

## RAKE-012: pipeline/embed.py - Stage 4: Embed
**Status:** BACKLOG
**Priority:** P1
**Owner:** Claude
**Area:** Pipeline
**Files:** `rake/pipeline/embed.py`
**Deps:** RAKE-006, RAKE-016

### Acceptance:
- [ ] embed_stage() async function
- [ ] Batch processing (100 chunks/batch)
- [ ] OpenAI API integration
- [ ] Cost tracking
- [ ] Returns List[Embedding]

**Notes:** Vector generation with OpenAI.

---

## RAKE-013: pipeline/store.py - Stage 5: Store
**Status:** BACKLOG
**Priority:** P1
**Owner:** Claude
**Area:** Pipeline
**Files:** `rake/pipeline/store.py`
**Deps:** RAKE-006, RAKE-015

### Acceptance:
- [ ] store_stage() async function
- [ ] DataForge API integration
- [ ] Multi-tenant support
- [ ] Bulk insert optimization
- [ ] Success confirmation

**Notes:** Final stage - persist to DataForge.

---

## RAKE-014: pipeline/orchestrator.py - Pipeline Coordination
**Status:** BACKLOG
**Priority:** P1
**Owner:** Claude
**Area:** Pipeline
**Files:** `rake/pipeline/orchestrator.py`
**Deps:** RAKE-009, RAKE-010, RAKE-011, RAKE-012, RAKE-013

### Acceptance:
- [ ] PipelineOrchestrator class
- [ ] run_pipeline() async method
- [ ] Stage-by-stage execution
- [ ] Error handling between stages
- [ ] Progress tracking
- [ ] Telemetry for each stage

**Notes:** Coordinates all 5 pipeline stages.

---

## RAKE-015: services/dataforge_client.py - DataForge API Client
**Status:** BACKLOG
**Priority:** P1
**Owner:** Claude
**Area:** Services
**Files:** `rake/services/dataforge_client.py`
**Deps:** RAKE-002

### Acceptance:
- [ ] DataForgeClient class
- [ ] store_embeddings() method
- [ ] query_knowledge_base() method
- [ ] Async HTTP client (httpx)
- [ ] Retry logic
- [ ] Multi-tenant support

**Notes:** Client for DataForge vector storage.

---

## RAKE-016: services/embedding_service.py - OpenAI Embeddings
**Status:** BACKLOG
**Priority:** P1
**Owner:** Claude
**Area:** Services
**Files:** `rake/services/embedding_service.py`
**Deps:** RAKE-002

### Acceptance:
- [ ] EmbeddingService class
- [ ] generate_embeddings() async method
- [ ] Batch processing
- [ ] Rate limiting
- [ ] Cost tracking
- [ ] Model selection

**Notes:** OpenAI embedding generation service.

---

## RAKE-017: api/routes.py - REST Endpoints
**Status:** BACKLOG
**Priority:** P2
**Owner:** Claude
**Area:** API
**Files:** `rake/api/routes.py`, `rake/api/dependencies.py`
**Deps:** RAKE-014

### Acceptance:
- [ ] POST /api/v1/jobs - Submit job
- [ ] GET /api/v1/jobs/{job_id} - Get status
- [ ] GET /api/v1/jobs - List jobs
- [ ] Authentication middleware
- [ ] Tenant context extraction

**Notes:** RESTful API for job management.

---

## RAKE-018: scheduler.py - Job Scheduling
**Status:** BACKLOG
**Priority:** P2
**Owner:** Claude
**Area:** Scheduling
**Files:** `rake/scheduler.py`
**Deps:** RAKE-014

### Acceptance:
- [ ] APScheduler integration
- [ ] Cron job support
- [ ] Job persistence
- [ ] Retry failed jobs
- [ ] Status monitoring

**Notes:** Scheduled data ingestion.

---

## RAKE-019: tests/ - Test Suite
**Status:** BACKLOG
**Priority:** P2
**Owner:** Claude
**Area:** Testing
**Files:** `rake/tests/conftest.py`, `rake/tests/unit/`, `rake/tests/integration/`
**Deps:** All previous tasks

### Acceptance:
- [ ] Pytest configuration
- [ ] Unit tests for each module
- [ ] Integration tests for pipeline
- [ ] Mock fixtures
- [ ] Coverage >80%

**Notes:** Comprehensive test coverage.

---

**Last updated:** 2025-12-03
**Phase:** 1 (Foundation)
**Active tasks:** 0
**Completed:** 0 / 19
