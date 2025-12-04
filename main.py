"""
Rake V1 - Automated Data Ingestion Pipeline

FastAPI application entry point for the Rake service. This service handles the
complete data ingestion pipeline from fetching documents to storing embeddings
in DataForge.

5-Stage Pipeline:
    1. FETCH  → Retrieve documents from sources
    2. CLEAN  → Normalize and clean text content
    3. CHUNK  → Split documents into semantic segments
    4. EMBED  → Generate vector embeddings
    5. STORE  → Persist to DataForge (PostgreSQL + pgvector)

Example:
    Run the service with:

    $ uvicorn main:app --host 0.0.0.0 --port 8002 --reload

    Or in production:

    $ uvicorn main:app --host 0.0.0.0 --port 8002 --workers 4
"""

import logging
import sys
from contextlib import asynccontextmanager
from datetime import datetime
from typing import AsyncGenerator, Dict, Any
from uuid import uuid4

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn

from config import settings

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manage application lifespan events.

    This async context manager handles startup and shutdown operations for the
    Rake service, including database connections, scheduler initialization, and
    graceful shutdown.

    Args:
        app: FastAPI application instance

    Yields:
        None: Control is yielded during application runtime

    Example:
        This is automatically called by FastAPI:

        >>> app = FastAPI(lifespan=lifespan)
        >>> # Startup code runs when app starts
        >>> # Shutdown code runs when app stops
    """
    # Startup
    correlation_id = str(uuid4())
    logger.info(
        "Starting Rake service",
        extra={
            "correlation_id": correlation_id,
            "version": settings.VERSION,
            "port": settings.RAKE_PORT,
            "environment": settings.ENVIRONMENT
        }
    )

    try:
        # Initialize services
        logger.info(
            "Initializing services",
            extra={"correlation_id": correlation_id}
        )

        # TODO: Initialize database connection pool
        # TODO: Initialize scheduler if enabled
        # TODO: Verify DataForge connectivity
        # TODO: Verify OpenAI API key

        logger.info(
            "Rake service started successfully",
            extra={"correlation_id": correlation_id}
        )

        yield

    except Exception as e:
        logger.error(
            f"Failed to start Rake service: {str(e)}",
            extra={"correlation_id": correlation_id},
            exc_info=True
        )
        raise

    finally:
        # Shutdown
        logger.info(
            "Shutting down Rake service",
            extra={"correlation_id": correlation_id}
        )

        try:
            # TODO: Close database connections
            # TODO: Shutdown scheduler gracefully
            # TODO: Complete in-flight jobs

            logger.info(
                "Rake service shutdown complete",
                extra={"correlation_id": correlation_id}
            )

        except Exception as e:
            logger.error(
                f"Error during shutdown: {str(e)}",
                extra={"correlation_id": correlation_id},
                exc_info=True
            )


# Create FastAPI application
app = FastAPI(
    title="Rake - Data Ingestion Pipeline",
    description=(
        "Automated data ingestion pipeline for the Forge Ecosystem. "
        "Fetches, cleans, chunks, embeds, and stores documents in DataForge."
    ),
    version=settings.VERSION,
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_correlation_id(request: Request, call_next):
    """Add correlation ID to all requests for distributed tracing.

    This middleware ensures every request has a unique correlation_id that can
    be used to trace operations across the entire pipeline and related services.

    Args:
        request: Incoming HTTP request
        call_next: Next middleware or route handler

    Returns:
        Response with X-Correlation-ID header

    Example:
        The correlation_id is automatically added to logs:

        >>> logger.info("Processing request", extra={"correlation_id": correlation_id})
    """
    correlation_id = request.headers.get("X-Correlation-ID") or str(uuid4())
    request.state.correlation_id = correlation_id

    response = await call_next(request)
    response.headers["X-Correlation-ID"] = correlation_id

    return response


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Global exception handler for unhandled errors.

    Catches all unhandled exceptions and returns a standardized error response
    with correlation ID for debugging.

    Args:
        request: The request that caused the exception
        exc: The exception that was raised

    Returns:
        JSONResponse with error details and correlation ID

    Example:
        Automatically handles exceptions:

        >>> raise ValueError("Invalid input")
        >>> # Returns: {"error": "Internal server error", "correlation_id": "..."}
    """
    correlation_id = getattr(request.state, "correlation_id", str(uuid4()))

    logger.error(
        f"Unhandled exception: {str(exc)}",
        extra={"correlation_id": correlation_id},
        exc_info=True
    )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Internal server error",
            "message": str(exc) if settings.ENVIRONMENT == "development" else "An unexpected error occurred",
            "correlation_id": correlation_id,
            "timestamp": datetime.utcnow().isoformat()
        }
    )


@app.get("/health", tags=["Health"])
async def health_check() -> Dict[str, Any]:
    """Health check endpoint for service monitoring.

    Returns the current health status of the Rake service, including connectivity
    to dependent services (DataForge, database, OpenAI).

    Returns:
        Dict containing:
            - status: "healthy" or "unhealthy"
            - version: Service version
            - timestamp: Current UTC timestamp
            - dependencies: Health status of dependent services

    Example:
        >>> response = await client.get("/health")
        >>> print(response.json())
        {
            "status": "healthy",
            "version": "1.0.0",
            "timestamp": "2025-12-03T10:00:00",
            "dependencies": {
                "database": "healthy",
                "dataforge": "healthy",
                "openai": "healthy"
            }
        }
    """
    # TODO: Check database connectivity
    # TODO: Check DataForge connectivity
    # TODO: Check OpenAI API availability

    dependencies = {
        "database": "unknown",
        "dataforge": "unknown",
        "openai": "unknown"
    }

    overall_status = "healthy"  # TODO: Determine based on dependency checks

    return {
        "status": overall_status,
        "service": "rake",
        "version": settings.VERSION,
        "timestamp": datetime.utcnow().isoformat(),
        "dependencies": dependencies
    }


@app.get("/", tags=["Root"])
async def root() -> Dict[str, str]:
    """Root endpoint with service information.

    Returns:
        Dict with service name and version

    Example:
        >>> response = await client.get("/")
        >>> print(response.json())
        {"service": "rake", "version": "1.0.0"}
    """
    return {
        "service": "rake",
        "version": settings.VERSION,
        "description": "Automated Data Ingestion Pipeline for Forge Ecosystem"
    }


# Import and include API routes
from api import router as api_router
app.include_router(api_router)


if __name__ == "__main__":
    """Run the application directly with uvicorn.

    This is useful for development. In production, use:

    $ uvicorn main:app --host 0.0.0.0 --port 8002 --workers 4

    Example:
        Run in development mode:

        $ python main.py
    """
    uvicorn.run(
        "main:app",
        host=settings.RAKE_HOST,
        port=settings.RAKE_PORT,
        reload=settings.ENVIRONMENT == "development",
        log_level=settings.LOG_LEVEL.lower()
    )
