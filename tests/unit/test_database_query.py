"""
Unit Tests for Database Query Adapter

Tests all functionality of the DatabaseQueryAdapter including connection
pooling, query execution, security validation, and error handling.

Coverage:
    - Initialization and configuration
    - Input validation (connection strings, queries, security)
    - Connection pooling and caching
    - Query execution (parameterized, timeouts)
    - Row-to-document conversion
    - Security features (read-only mode, query validation)
    - Error handling
    - Health checks
    - Connection cleanup

Example:
    >>> pytest tests/unit/test_database_query.py -v --cov=sources.database_query
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import List, Dict, Any

from sources.database_query import DatabaseQueryAdapter
from sources.base import FetchError, ValidationError
from models.document import DocumentSource, RawDocument


# ============================================================================
# INITIALIZATION TESTS
# ============================================================================


class TestDatabaseQueryAdapterInit:
    """Test adapter initialization and configuration."""

    def test_init_default_params(self):
        """Test initialization with default parameters."""
        adapter = DatabaseQueryAdapter(tenant_id="tenant-123")

        assert adapter.tenant_id == "tenant-123"
        assert adapter.source_type == DocumentSource.DATABASE_QUERY
        assert adapter.max_rows == 1000
        assert adapter.read_only is True
        assert adapter.timeout == 30.0
        assert adapter.pool_size == 5
        assert adapter.max_overflow == 10
        assert adapter._engines == {}

    def test_init_custom_params(self):
        """Test initialization with custom parameters."""
        adapter = DatabaseQueryAdapter(
            tenant_id="tenant-456",
            max_rows=500,
            read_only=False,
            timeout=60.0,
            pool_size=10,
            max_overflow=20
        )

        assert adapter.tenant_id == "tenant-456"
        assert adapter.max_rows == 500
        assert adapter.read_only is False
        assert adapter.timeout == 60.0
        assert adapter.pool_size == 10
        assert adapter.max_overflow == 20

    def test_init_max_rows_hard_limit(self):
        """Test that max_rows is capped at 10000."""
        adapter = DatabaseQueryAdapter(max_rows=50000)
        assert adapter.max_rows == 10000  # Hard limit

    def test_init_no_tenant(self):
        """Test initialization without tenant_id."""
        adapter = DatabaseQueryAdapter()
        assert adapter.tenant_id is None


# ============================================================================
# VALIDATION TESTS
# ============================================================================


class TestValidateInput:
    """Test input validation."""

    @pytest.mark.asyncio
    async def test_validate_missing_connection_string(self):
        """Test validation fails when connection_string is missing."""
        adapter = DatabaseQueryAdapter()

        with pytest.raises(ValidationError) as exc_info:
            await adapter._validate_input(
                connection_string=None,
                query="SELECT * FROM users"
            )

        assert "connection_string is required" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_validate_missing_query(self):
        """Test validation fails when query is missing."""
        adapter = DatabaseQueryAdapter()

        with pytest.raises(ValidationError) as exc_info:
            await adapter._validate_input(
                connection_string="postgresql://localhost/db",
                query=None
            )

        assert "query is required" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_validate_invalid_connection_string(self):
        """Test validation fails for invalid connection string format."""
        adapter = DatabaseQueryAdapter()

        with pytest.raises(ValidationError) as exc_info:
            await adapter._validate_input(
                connection_string="invalid://localhost/db",
                query="SELECT * FROM users"
            )

        assert "Invalid connection_string" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_validate_valid_connection_strings(self):
        """Test validation passes for valid connection strings."""
        adapter = DatabaseQueryAdapter()

        # PostgreSQL
        await adapter._validate_input(
            connection_string="postgresql://localhost/db",
            query="SELECT * FROM users"
        )

        # MySQL
        await adapter._validate_input(
            connection_string="mysql://localhost/db",
            query="SELECT * FROM users"
        )

        # SQLite
        await adapter._validate_input(
            connection_string="sqlite:///path/to/db.sqlite",
            query="SELECT * FROM users"
        )

    @pytest.mark.asyncio
    async def test_validate_read_only_mode_non_select(self):
        """Test validation fails for non-SELECT queries in read-only mode."""
        adapter = DatabaseQueryAdapter(read_only=True)

        with pytest.raises(ValidationError) as exc_info:
            await adapter._validate_input(
                connection_string="postgresql://localhost/db",
                query="DELETE FROM users WHERE id = 1"
            )

        assert "Only SELECT queries allowed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_validate_read_only_mode_dangerous_keywords(self):
        """Test validation fails for queries with dangerous keywords."""
        adapter = DatabaseQueryAdapter(read_only=True)

        dangerous_queries = [
            "SELECT * FROM users; DROP TABLE users;",
            "SELECT * FROM (DELETE FROM users) AS t",
            "INSERT INTO logs SELECT * FROM users",
            "UPDATE users SET name = (SELECT name FROM admins)",
            "TRUNCATE TABLE users; SELECT * FROM admins;",
            "ALTER TABLE users ADD COLUMN hacked VARCHAR(255)"
        ]

        for query in dangerous_queries:
            with pytest.raises(ValidationError) as exc_info:
                await adapter._validate_input(
                    connection_string="postgresql://localhost/db",
                    query=query
                )

            assert "forbidden keyword" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_validate_non_read_only_allows_modifications(self):
        """Test that non-read-only mode allows modification queries."""
        adapter = DatabaseQueryAdapter(read_only=False)

        # Should not raise
        await adapter._validate_input(
            connection_string="postgresql://localhost/db",
            query="DELETE FROM users WHERE id = 1"
        )


# ============================================================================
# CONNECTION TESTS
# ============================================================================


class TestGetEngine:
    """Test database engine creation and caching."""

    @patch('sources.database_query.create_engine')
    def test_get_engine_creates_new(self, mock_create_engine):
        """Test that _get_engine creates new engine."""
        adapter = DatabaseQueryAdapter()
        mock_engine = Mock()
        mock_create_engine.return_value = mock_engine

        connection_string = "postgresql://localhost/db"
        engine = adapter._get_engine(connection_string)

        assert engine == mock_engine
        mock_create_engine.assert_called_once()
        assert adapter._engines[connection_string] == mock_engine

    @patch('sources.database_query.create_engine')
    def test_get_engine_caches(self, mock_create_engine):
        """Test that _get_engine returns cached engine."""
        adapter = DatabaseQueryAdapter()
        mock_engine = Mock()
        mock_create_engine.return_value = mock_engine

        connection_string = "postgresql://localhost/db"

        # First call creates engine
        engine1 = adapter._get_engine(connection_string)
        # Second call returns cached engine
        engine2 = adapter._get_engine(connection_string)

        assert engine1 == engine2
        mock_create_engine.assert_called_once()  # Only called once

    @patch('sources.database_query.create_engine')
    def test_get_engine_handles_error(self, mock_create_engine):
        """Test that _get_engine handles creation errors."""
        adapter = DatabaseQueryAdapter()
        mock_create_engine.side_effect = Exception("Connection failed")

        with pytest.raises(FetchError) as exc_info:
            adapter._get_engine("postgresql://localhost/db")

        assert "Failed to create database engine" in str(exc_info.value)


# ============================================================================
# CONNECTION STRING MASKING TESTS
# ============================================================================


class TestMaskConnectionString:
    """Test connection string password masking."""

    def test_mask_connection_string_with_password(self):
        """Test masking connection string with password."""
        adapter = DatabaseQueryAdapter()

        masked = adapter._mask_connection_string(
            "postgresql://user:password123@localhost:5432/db"
        )

        assert "password123" not in masked
        assert "***" in masked
        assert "postgresql://user:***@localhost:5432/db" == masked

    def test_mask_connection_string_no_password(self):
        """Test masking connection string without password."""
        adapter = DatabaseQueryAdapter()

        connection_string = "sqlite:///path/to/db.sqlite"
        masked = adapter._mask_connection_string(connection_string)

        assert masked == connection_string  # No change

    def test_mask_connection_string_no_auth(self):
        """Test masking connection string without authentication."""
        adapter = DatabaseQueryAdapter()

        connection_string = "postgresql://localhost/db"
        masked = adapter._mask_connection_string(connection_string)

        assert masked == connection_string  # No change


# ============================================================================
# QUERY EXECUTION TESTS
# ============================================================================


class TestExecuteQuery:
    """Test SQL query execution."""

    def test_execute_query_postgresql(self):
        """Test executing query on PostgreSQL."""
        adapter = DatabaseQueryAdapter(timeout=10.0)

        # Mock engine and connection
        mock_engine = Mock()
        mock_engine.url = Mock()
        mock_engine.url.__str__ = Mock(return_value="postgresql://localhost/db")

        mock_connection = Mock()
        mock_result = Mock()
        mock_connection.execute.return_value = mock_result
        mock_engine.connect.return_value.__enter__ = Mock(return_value=mock_connection)
        mock_engine.connect.return_value.__exit__ = Mock(return_value=False)

        # Execute query
        result = adapter._execute_query(
            engine=mock_engine,
            query="SELECT * FROM users",
            params=None
        )

        assert result == mock_result
        # Should set PostgreSQL timeout
        assert mock_connection.execute.call_count == 2  # Timeout + query

    def test_execute_query_mysql(self):
        """Test executing query on MySQL."""
        adapter = DatabaseQueryAdapter(timeout=10.0)

        # Mock engine and connection
        mock_engine = Mock()
        mock_engine.url = Mock()
        mock_engine.url.__str__ = Mock(return_value="mysql://localhost/db")

        mock_connection = Mock()
        mock_result = Mock()
        mock_connection.execute.return_value = mock_result
        mock_engine.connect.return_value.__enter__ = Mock(return_value=mock_connection)
        mock_engine.connect.return_value.__exit__ = Mock(return_value=False)

        # Execute query
        result = adapter._execute_query(
            engine=mock_engine,
            query="SELECT * FROM users",
            params=None
        )

        assert result == mock_result
        # Should set MySQL timeout
        assert mock_connection.execute.call_count == 2  # Timeout + query

    def test_execute_query_with_params(self):
        """Test executing parameterized query."""
        adapter = DatabaseQueryAdapter()

        # Mock engine and connection
        mock_engine = Mock()
        mock_engine.url = Mock()
        mock_engine.url.__str__ = Mock(return_value="sqlite:///db.sqlite")

        mock_connection = Mock()
        mock_result = Mock()
        mock_connection.execute.return_value = mock_result
        mock_engine.connect.return_value.__enter__ = Mock(return_value=mock_connection)
        mock_engine.connect.return_value.__exit__ = Mock(return_value=False)

        # Execute query with parameters
        params = {"user_id": 123}
        result = adapter._execute_query(
            engine=mock_engine,
            query="SELECT * FROM users WHERE id = :user_id",
            params=params
        )

        assert result == mock_result

    def test_execute_query_timeout_error(self):
        """Test handling query timeout errors."""
        adapter = DatabaseQueryAdapter()

        # Mock engine that raises timeout error
        mock_engine = Mock()
        mock_engine.url = Mock()
        mock_engine.url.__str__ = Mock(return_value="postgresql://localhost/db")

        from sqlalchemy.exc import OperationalError
        mock_connection = Mock()
        mock_connection.execute.side_effect = OperationalError(
            "statement", "params", "timeout occurred"
        )
        mock_engine.connect.return_value.__enter__ = Mock(return_value=mock_connection)
        mock_engine.connect.return_value.__exit__ = Mock(return_value=False)

        with pytest.raises(FetchError) as exc_info:
            adapter._execute_query(
                engine=mock_engine,
                query="SELECT * FROM users"
            )

        assert "timeout" in str(exc_info.value).lower()


# ============================================================================
# ROW TO DOCUMENT CONVERSION TESTS
# ============================================================================


class TestRowToDocument:
    """Test database row to RawDocument conversion."""

    def test_row_to_document_basic(self):
        """Test converting basic database row to document."""
        adapter = DatabaseQueryAdapter(tenant_id="tenant-123")

        row = {
            "id": 1,
            "title": "Test Article",
            "content": "This is test content"
        }

        doc = adapter._row_to_document(
            row=row,
            row_number=1,
            content_column="content",
            title_column="title",
            id_column="id"
        )

        assert isinstance(doc, RawDocument)
        assert doc.content == "This is test content"
        assert doc.source == DocumentSource.DATABASE_QUERY
        assert doc.tenant_id == "tenant-123"
        assert doc.metadata["title"] == "Test Article"
        assert doc.metadata["row_number"] == 1
        assert doc.metadata["row_data"] == row

    def test_row_to_document_fallback_columns(self):
        """Test fallback to common column names."""
        adapter = DatabaseQueryAdapter()

        row = {
            "id": 1,
            "title": "Article",
            "body": "Content in body column"  # Should fallback to 'body'
        }

        doc = adapter._row_to_document(
            row=row,
            row_number=1,
            content_column="content",  # Not in row
            title_column="title"
        )

        assert doc.content == "Content in body column"

    def test_row_to_document_json_fallback(self):
        """Test JSON serialization fallback when no content column found."""
        adapter = DatabaseQueryAdapter()

        row = {
            "id": 1,
            "name": "John Doe",
            "email": "john@example.com"
        }

        doc = adapter._row_to_document(
            row=row,
            row_number=1,
            content_column="content",  # Not in row
            title_column="title"  # Not in row
        )

        # Content should be JSON serialization of row
        assert "John Doe" in doc.content
        assert "john@example.com" in doc.content

    def test_row_to_document_custom_metadata(self):
        """Test adding additional metadata."""
        adapter = DatabaseQueryAdapter()

        row = {"id": 1, "content": "Test"}
        additional_metadata = {"custom_field": "custom_value"}

        doc = adapter._row_to_document(
            row=row,
            row_number=1,
            additional_metadata=additional_metadata
        )

        assert doc.metadata["custom_field"] == "custom_value"

    def test_row_to_document_no_id_column(self):
        """Test document ID generation when id_column is None."""
        adapter = DatabaseQueryAdapter()

        row = {"content": "Test"}

        doc = adapter._row_to_document(
            row=row,
            row_number=42,
            id_column=None
        )

        assert "db-row-42" in doc.id


# ============================================================================
# FETCH TESTS
# ============================================================================


class TestFetch:
    """Test main fetch method."""

    @pytest.mark.asyncio
    async def test_fetch_basic(self):
        """Test basic fetch operation."""
        adapter = DatabaseQueryAdapter(tenant_id="tenant-123")

        # Mock engine and query execution
        with patch.object(adapter, '_get_engine') as mock_get_engine, \
             patch.object(adapter, '_execute_query') as mock_execute_query:

            # Mock result rows
            mock_row1 = Mock()
            mock_row1._mapping = {"id": 1, "title": "Doc 1", "content": "Content 1"}
            mock_row2 = Mock()
            mock_row2._mapping = {"id": 2, "title": "Doc 2", "content": "Content 2"}

            mock_result = [mock_row1, mock_row2]
            mock_execute_query.return_value = mock_result

            # Execute fetch
            documents = await adapter.fetch(
                connection_string="postgresql://localhost/db",
                query="SELECT * FROM articles",
                content_column="content",
                title_column="title",
                id_column="id"
            )

            assert len(documents) == 2
            assert all(isinstance(doc, RawDocument) for doc in documents)
            assert documents[0].content == "Content 1"
            assert documents[1].content == "Content 2"

    @pytest.mark.asyncio
    async def test_fetch_with_params(self):
        """Test fetch with parameterized query."""
        adapter = DatabaseQueryAdapter()

        with patch.object(adapter, '_get_engine') as mock_get_engine, \
             patch.object(adapter, '_execute_query') as mock_execute_query:

            mock_row = Mock()
            mock_row._mapping = {"id": 1, "content": "Test"}
            mock_execute_query.return_value = [mock_row]

            params = {"user_id": 123}
            documents = await adapter.fetch(
                connection_string="postgresql://localhost/db",
                query="SELECT * FROM articles WHERE user_id = :user_id",
                params=params
            )

            # Verify params were passed
            call_args = mock_execute_query.call_args
            assert call_args[1]["params"] == params

    @pytest.mark.asyncio
    async def test_fetch_max_rows_limit(self):
        """Test that fetch respects max_rows limit."""
        adapter = DatabaseQueryAdapter(max_rows=2)

        with patch.object(adapter, '_get_engine'), \
             patch.object(adapter, '_execute_query') as mock_execute_query:

            # Mock 5 rows
            mock_rows = []
            for i in range(5):
                mock_row = Mock()
                mock_row._mapping = {"id": i, "content": f"Content {i}"}
                mock_rows.append(mock_row)

            mock_execute_query.return_value = mock_rows

            documents = await adapter.fetch(
                connection_string="postgresql://localhost/db",
                query="SELECT * FROM articles"
            )

            # Should only return 2 documents (max_rows limit)
            assert len(documents) == 2

    @pytest.mark.asyncio
    async def test_fetch_override_max_rows(self):
        """Test overriding max_rows per request."""
        adapter = DatabaseQueryAdapter(max_rows=1000)

        with patch.object(adapter, '_get_engine'), \
             patch.object(adapter, '_execute_query') as mock_execute_query:

            # Mock 3 rows
            mock_rows = []
            for i in range(3):
                mock_row = Mock()
                mock_row._mapping = {"id": i, "content": f"Content {i}"}
                mock_rows.append(mock_row)

            mock_execute_query.return_value = mock_rows

            documents = await adapter.fetch(
                connection_string="postgresql://localhost/db",
                query="SELECT * FROM articles",
                max_rows=2  # Override to 2
            )

            # Should return 2 documents
            assert len(documents) == 2

    @pytest.mark.asyncio
    async def test_fetch_validation_error(self):
        """Test that fetch raises validation errors."""
        adapter = DatabaseQueryAdapter()

        with pytest.raises(ValidationError):
            await adapter.fetch(
                connection_string=None,  # Missing
                query="SELECT * FROM users"
            )

    @pytest.mark.asyncio
    async def test_fetch_handles_unexpected_error(self):
        """Test that fetch handles unexpected errors."""
        adapter = DatabaseQueryAdapter()

        with patch.object(adapter, '_get_engine') as mock_get_engine:
            mock_get_engine.side_effect = Exception("Unexpected error")

            with pytest.raises(FetchError) as exc_info:
                await adapter.fetch(
                    connection_string="postgresql://localhost/db",
                    query="SELECT * FROM users"
                )

            assert "Unexpected error" in str(exc_info.value)


# ============================================================================
# HEALTH CHECK TESTS
# ============================================================================


class TestHealthCheck:
    """Test health check functionality."""

    @pytest.mark.asyncio
    async def test_health_check_success(self):
        """Test successful health check."""
        adapter = DatabaseQueryAdapter()

        with patch('sources.database_query.create_engine') as mock_create_engine:
            # Mock successful connection
            mock_engine = Mock()
            mock_connection = Mock()
            mock_engine.connect.return_value.__enter__ = Mock(return_value=mock_connection)
            mock_engine.connect.return_value.__exit__ = Mock(return_value=False)
            mock_create_engine.return_value = mock_engine

            is_healthy = await adapter.health_check()

            assert is_healthy is True

    @pytest.mark.asyncio
    async def test_health_check_failure(self):
        """Test failed health check."""
        adapter = DatabaseQueryAdapter()

        with patch('sources.database_query.create_engine') as mock_create_engine:
            # Mock connection failure
            mock_create_engine.side_effect = Exception("Connection failed")

            is_healthy = await adapter.health_check()

            assert is_healthy is False


# ============================================================================
# SUPPORTED DATABASES TESTS
# ============================================================================


class TestGetSupportedDatabases:
    """Test get_supported_databases method."""

    def test_get_supported_databases(self):
        """Test that supported databases are returned."""
        adapter = DatabaseQueryAdapter()

        databases = adapter.get_supported_databases()

        assert "postgresql" in databases
        assert "mysql" in databases
        assert "sqlite" in databases
        assert len(databases) == 3


# ============================================================================
# CLOSE TESTS
# ============================================================================


class TestClose:
    """Test connection cleanup."""

    @pytest.mark.asyncio
    async def test_close_disposes_engines(self):
        """Test that close disposes all engines."""
        adapter = DatabaseQueryAdapter()

        # Add mock engines
        mock_engine1 = Mock()
        mock_engine2 = Mock()
        adapter._engines = {
            "postgresql://localhost/db1": mock_engine1,
            "postgresql://localhost/db2": mock_engine2,
        }

        await adapter.close()

        # Should dispose both engines
        mock_engine1.dispose.assert_called_once()
        mock_engine2.dispose.assert_called_once()

        # Should clear cache
        assert adapter._engines == {}

    @pytest.mark.asyncio
    async def test_close_handles_dispose_error(self):
        """Test that close handles dispose errors gracefully."""
        adapter = DatabaseQueryAdapter()

        # Mock engine that fails to dispose
        mock_engine = Mock()
        mock_engine.dispose.side_effect = Exception("Dispose failed")
        adapter._engines = {"postgresql://localhost/db": mock_engine}

        # Should not raise
        await adapter.close()

        # Should still clear cache
        assert adapter._engines == {}
