"""
Database Query Source Adapter

Executes SQL queries against various database systems and ingests results
into the Rake pipeline. Supports PostgreSQL, MySQL, and SQLite.

Example:
    >>> from sources.database_query import DatabaseQueryAdapter
    >>> adapter = DatabaseQueryAdapter(tenant_id="tenant-123")
    >>> documents = await adapter.fetch(
    ...     connection_string="postgresql://user:pass@localhost/db",
    ...     query="SELECT * FROM articles WHERE published = true",
    ...     content_column="body",
    ...     title_column="title"
    ... )
"""

import logging
import time
from typing import List, Dict, Any, Optional
from uuid import uuid4
import asyncio

from sqlalchemy import create_engine, text, MetaData, Table
from sqlalchemy.engine import Engine, Result
from sqlalchemy.pool import QueuePool
from sqlalchemy.exc import SQLAlchemyError, OperationalError

from models.document import RawDocument, DocumentSource
from sources.base import BaseSourceAdapter, FetchError, ValidationError

logger = logging.getLogger(__name__)


class DatabaseQueryAdapter(BaseSourceAdapter):
    """Adapter for fetching data from database queries.

    Executes SQL queries against various database systems (PostgreSQL,
    MySQL, SQLite) and converts result rows to documents.

    Attributes:
        tenant_id: Multi-tenant identifier
        max_rows: Maximum rows to fetch per query
        read_only: Whether to allow only SELECT queries
        timeout: Query timeout in seconds

    Example:
        >>> adapter = DatabaseQueryAdapter(
        ...     tenant_id="tenant-123",
        ...     max_rows=1000,
        ...     read_only=True
        ... )
        >>> documents = await adapter.fetch(
        ...     connection_string="postgresql://localhost/mydb",
        ...     query="SELECT id, title, content FROM articles"
        ... )
    """

    def __init__(
        self,
        tenant_id: Optional[str] = None,
        max_rows: int = 1000,
        read_only: bool = True,
        timeout: float = 30.0,
        pool_size: int = 5,
        max_overflow: int = 10
    ):
        """Initialize database query adapter.

        Args:
            tenant_id: Multi-tenant identifier
            max_rows: Maximum rows to fetch (1-10000)
            read_only: Only allow SELECT queries
            timeout: Query timeout in seconds
            pool_size: Connection pool size
            max_overflow: Max overflow connections

        Example:
            >>> adapter = DatabaseQueryAdapter(
            ...     tenant_id="tenant-456",
            ...     max_rows=500,
            ...     read_only=True,
            ...     timeout=60.0
            ... )
        """
        super().__init__(tenant_id=tenant_id)
        self.source_type = DocumentSource.DATABASE_QUERY
        self.max_rows = min(max_rows, 10000)  # Hard limit
        self.read_only = read_only
        self.timeout = timeout
        self.pool_size = pool_size
        self.max_overflow = max_overflow
        self.logger = logging.getLogger(__name__)

        # Connection pool cache
        self._engines: Dict[str, Engine] = {}

        self.logger.info(
            f"DatabaseQueryAdapter initialized with max_rows={max_rows}, "
            f"read_only={read_only}, timeout={timeout}s"
        )

    async def _validate_input(
        self,
        connection_string: Optional[str] = None,
        query: Optional[str] = None,
        **kwargs
    ) -> None:
        """Validate input parameters.

        Args:
            connection_string: Database connection string
            query: SQL query to execute
            **kwargs: Additional parameters

        Raises:
            ValidationError: If validation fails

        Example:
            >>> await adapter._validate_input(
            ...     connection_string="postgresql://localhost/db",
            ...     query="SELECT * FROM users"
            ... )
        """
        if not connection_string:
            raise ValidationError("connection_string is required for database queries")

        if not query:
            raise ValidationError("query is required for database queries")

        # Validate connection string format
        if not connection_string.startswith(("postgresql://", "mysql://", "sqlite:///")):
            raise ValidationError(
                "Invalid connection_string. Must start with postgresql://, "
                "mysql://, or sqlite:///"
            )

        # Validate query if read-only mode
        if self.read_only:
            query_upper = query.strip().upper()
            if not query_upper.startswith("SELECT"):
                raise ValidationError(
                    "Only SELECT queries allowed in read-only mode. "
                    f"Query starts with: {query_upper.split()[0]}"
                )

            # Check for dangerous keywords
            dangerous_keywords = ["DROP", "DELETE", "INSERT", "UPDATE", "TRUNCATE", "ALTER"]
            for keyword in dangerous_keywords:
                if keyword in query_upper:
                    raise ValidationError(
                        f"Query contains forbidden keyword: {keyword} "
                        "(read-only mode enabled)"
                    )

    def _get_engine(self, connection_string: str) -> Engine:
        """Get or create database engine with connection pooling.

        Args:
            connection_string: Database connection string

        Returns:
            SQLAlchemy Engine instance

        Example:
            >>> engine = adapter._get_engine("postgresql://localhost/db")
        """
        # Use cached engine if available
        if connection_string in self._engines:
            return self._engines[connection_string]

        # Create new engine with connection pooling
        try:
            engine = create_engine(
                connection_string,
                poolclass=QueuePool,
                pool_size=self.pool_size,
                max_overflow=self.max_overflow,
                pool_pre_ping=True,  # Verify connections before using
                pool_recycle=3600,  # Recycle connections after 1 hour
                connect_args={"connect_timeout": self.timeout}
            )

            self._engines[connection_string] = engine
            self.logger.info(f"Created database engine for {self._mask_connection_string(connection_string)}")
            return engine

        except SQLAlchemyError as e:
            raise FetchError(f"Failed to create database engine: {str(e)}")

    def _mask_connection_string(self, connection_string: str) -> str:
        """Mask password in connection string for logging.

        Args:
            connection_string: Full connection string

        Returns:
            Masked connection string

        Example:
            >>> masked = adapter._mask_connection_string(
            ...     "postgresql://user:password@localhost/db"
            ... )
            >>> print(masked)
            postgresql://user:***@localhost/db
        """
        if "://" in connection_string and "@" in connection_string:
            parts = connection_string.split("@")
            if ":" in parts[0]:
                user_pass = parts[0].split(":")
                return f"{':'.join(user_pass[:-1])}:***@{parts[1]}"

        return connection_string

    def _execute_query(
        self,
        engine: Engine,
        query: str,
        params: Optional[Dict[str, Any]] = None
    ) -> Result:
        """Execute SQL query with parameters.

        Args:
            engine: SQLAlchemy engine
            query: SQL query string
            params: Query parameters for parameterized queries

        Returns:
            Query result

        Raises:
            FetchError: If query execution fails

        Example:
            >>> result = adapter._execute_query(
            ...     engine,
            ...     "SELECT * FROM users WHERE id = :user_id",
            ...     params={"user_id": 123}
            ... )
        """
        try:
            with engine.connect() as connection:
                # Set query timeout
                if "postgresql" in str(engine.url):
                    connection.execute(text(f"SET statement_timeout = {int(self.timeout * 1000)}"))
                elif "mysql" in str(engine.url):
                    connection.execute(text(f"SET SESSION max_execution_time = {int(self.timeout * 1000)}"))

                # Execute query with parameters
                if params:
                    result = connection.execute(text(query), params)
                else:
                    result = connection.execute(text(query))

                return result

        except OperationalError as e:
            if "timeout" in str(e).lower() or "timed out" in str(e).lower():
                raise FetchError(f"Query timeout after {self.timeout}s: {str(e)}")
            raise FetchError(f"Database operational error: {str(e)}")

        except SQLAlchemyError as e:
            raise FetchError(f"Query execution failed: {str(e)}")

    def _row_to_document(
        self,
        row: Dict[str, Any],
        row_number: int,
        content_column: str = "content",
        title_column: str = "title",
        id_column: Optional[str] = "id",
        additional_metadata: Optional[Dict[str, Any]] = None
    ) -> RawDocument:
        """Convert database row to RawDocument.

        Args:
            row: Database row as dictionary
            row_number: Row number (for ID generation)
            content_column: Column containing content
            title_column: Column containing title
            id_column: Column containing unique ID
            additional_metadata: Additional metadata to attach

        Returns:
            RawDocument instance

        Example:
            >>> row = {"id": 1, "title": "Article", "body": "Content"}
            >>> doc = adapter._row_to_document(
            ...     row=row,
            ...     row_number=1,
            ...     content_column="body"
            ... )
        """
        # Extract content
        content = row.get(content_column, "")

        # Try common column names if content column not found
        if not content:
            for col in ["body", "text", "content", "description", "message"]:
                if col in row:
                    content = row[col]
                    break

        # If still no content, serialize entire row as JSON
        if not content:
            import json
            content = json.dumps(dict(row), default=str, indent=2)

        # Extract title
        title = row.get(title_column, "")

        # Extract ID
        doc_id = row.get(id_column, f"db-row-{row_number}") if id_column else f"db-row-{row_number}"

        # Build metadata
        metadata = {
            "row_number": row_number,
            "title": str(title) if title else "",
            "fetched_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "row_data": dict(row),  # Include full row data
        }

        # Add additional metadata
        if additional_metadata:
            metadata.update(additional_metadata)

        # Create document
        doc = RawDocument(
            id=f"db-{uuid4().hex[:12]}-{doc_id}",
            content=str(content),
            source=self.source_type,
            metadata=metadata,
            tenant_id=self.tenant_id
        )

        return doc

    async def fetch(
        self,
        connection_string: str,
        query: str,
        params: Optional[Dict[str, Any]] = None,
        content_column: str = "content",
        title_column: str = "title",
        id_column: Optional[str] = "id",
        max_rows: Optional[int] = None,
        **kwargs
    ) -> List[RawDocument]:
        """Execute database query and fetch results.

        Args:
            connection_string: Database connection string
            query: SQL query to execute
            params: Query parameters for parameterized queries
            content_column: Column name containing content
            title_column: Column name containing title
            id_column: Column name containing unique ID
            max_rows: Maximum rows to fetch (overrides instance max_rows)
            **kwargs: Additional parameters

        Returns:
            List of RawDocument objects

        Raises:
            FetchError: If query execution fails
            ValidationError: If validation fails

        Example:
            >>> documents = await adapter.fetch(
            ...     connection_string="postgresql://localhost/mydb",
            ...     query="SELECT id, title, body FROM articles WHERE published = :pub",
            ...     params={"pub": True},
            ...     content_column="body",
            ...     title_column="title",
            ...     id_column="id",
            ...     max_rows=100
            ... )
        """
        # Validate inputs
        await self._validate_input(
            connection_string=connection_string,
            query=query,
            **kwargs
        )

        # Determine max rows
        row_limit = min(max_rows or self.max_rows, self.max_rows)

        self.logger.info(
            f"Executing database query (max_rows={row_limit})",
            extra={
                "connection": self._mask_connection_string(connection_string),
                "query_preview": query[:100] + "..." if len(query) > 100 else query
            }
        )

        try:
            # Get database engine
            engine = self._get_engine(connection_string)

            # Execute query (run in executor to avoid blocking)
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                self._execute_query,
                engine,
                query,
                params
            )

            # Fetch rows (with limit)
            documents = []
            row_count = 0

            for row in result:
                if row_count >= row_limit:
                    self.logger.warning(
                        f"Reached max_rows limit ({row_limit}), stopping"
                    )
                    break

                # Convert row to dictionary
                row_dict = dict(row._mapping)

                # Convert to document
                doc = self._row_to_document(
                    row=row_dict,
                    row_number=row_count + 1,
                    content_column=content_column,
                    title_column=title_column,
                    id_column=id_column,
                    additional_metadata={
                        "connection": self._mask_connection_string(connection_string),
                        "query_hash": hash(query) % 10**8  # Query fingerprint
                    }
                )

                documents.append(doc)
                row_count += 1

            self.logger.info(
                f"Database query completed: {len(documents)} documents fetched"
            )

            return documents

        except FetchError:
            raise
        except Exception as e:
            self.logger.error(
                f"Unexpected error executing query: {str(e)}",
                exc_info=True
            )
            raise FetchError(f"Unexpected error: {str(e)}")

    async def health_check(self) -> bool:
        """Check if database connections are working.

        Returns:
            True if healthy, False otherwise

        Example:
            >>> is_healthy = await adapter.health_check()
        """
        try:
            # Try to create a simple SQLite connection as health check
            test_connection = "sqlite:///:memory:"
            engine = create_engine(test_connection)

            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))

            return True

        except Exception as e:
            self.logger.error(f"Health check failed: {str(e)}")
            return False

    def get_supported_databases(self) -> List[str]:
        """Get list of supported database systems.

        Returns:
            List of supported database identifiers

        Example:
            >>> databases = adapter.get_supported_databases()
            >>> print(databases)
            ['postgresql', 'mysql', 'sqlite']
        """
        return ["postgresql", "mysql", "sqlite"]

    async def close(self) -> None:
        """Close all database connections.

        Example:
            >>> await adapter.close()
        """
        for connection_string, engine in self._engines.items():
            try:
                engine.dispose()
                self.logger.info(
                    f"Closed database engine for {self._mask_connection_string(connection_string)}"
                )
            except Exception as e:
                self.logger.error(
                    f"Error closing engine: {str(e)}",
                    exc_info=True
                )

        self._engines.clear()
