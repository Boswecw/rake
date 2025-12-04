# Database Query Integration Guide

Complete guide for ingesting data from SQL databases into the Rake pipeline.

## Table of Contents

- [Overview](#overview)
- [Supported Databases](#supported-databases)
- [Quick Start](#quick-start)
- [Configuration](#configuration)
- [Security](#security)
- [Usage Examples](#usage-examples)
- [Column Mapping](#column-mapping)
- [Parameterized Queries](#parameterized-queries)
- [Error Handling](#error-handling)
- [Best Practices](#best-practices)
- [Troubleshooting](#troubleshooting)

---

## Overview

The Database Query Adapter enables direct ingestion of data from SQL databases into the Rake pipeline. It supports PostgreSQL, MySQL, and SQLite with built-in security features, connection pooling, and flexible column mapping.

### Features

- ✅ **Multiple Database Support**: PostgreSQL, MySQL, SQLite
- ✅ **Security First**: Read-only mode, query validation, SQL injection prevention
- ✅ **Connection Pooling**: Efficient resource management with automatic cleanup
- ✅ **Parameterized Queries**: Safe parameter binding to prevent SQL injection
- ✅ **Flexible Mapping**: Configure which columns map to content, title, and ID
- ✅ **Query Timeout**: Prevent runaway queries with configurable timeouts
- ✅ **Row Limits**: Hard limits to prevent excessive data fetching
- ✅ **Full Pipeline Integration**: FETCH → CLEAN → CHUNK → EMBED → STORE

---

## Supported Databases

### PostgreSQL

```python
connection_string = "postgresql://user:password@localhost:5432/database"
```

**Features**:
- Full query timeout support via `statement_timeout`
- Advanced features (CTEs, window functions, JSONB)
- Best for production workloads

### MySQL

```python
connection_string = "mysql://user:password@localhost:3306/database"
```

**Features**:
- Query timeout via `max_execution_time`
- Wide compatibility
- Good for web applications

### SQLite

```python
connection_string = "sqlite:///path/to/database.db"
```

**Features**:
- File-based, no server needed
- Perfect for development and testing
- Great for embedded use cases

---

## Quick Start

### Using the API (Recommended)

```bash
curl -X POST http://localhost:8002/api/v1/jobs \
  -H "Content-Type: application/json" \
  -d '{
    "source": "database_query",
    "tenant_id": "tenant-123",
    "connection_string": "postgresql://user:password@localhost/mydb",
    "query": "SELECT id, title, body FROM articles WHERE published = true",
    "db_content_column": "body",
    "db_title_column": "title",
    "db_id_column": "id",
    "db_max_rows": 100
  }'
```

### Using the Adapter Directly

```python
from sources.database_query import DatabaseQueryAdapter

# Initialize adapter
adapter = DatabaseQueryAdapter(
    tenant_id="tenant-123",
    max_rows=1000,
    read_only=True,  # Security: only allow SELECT
    timeout=30.0
)

# Fetch documents
documents = await adapter.fetch(
    connection_string="postgresql://localhost/mydb",
    query="SELECT id, title, content FROM articles",
    content_column="content",
    title_column="title",
    id_column="id"
)

print(f"Fetched {len(documents)} documents")

# Cleanup
await adapter.close()
```

---

## Configuration

### Environment Variables

Add to your `.env` file:

```bash
# Database Query Configuration
DB_QUERY_MAX_ROWS=1000           # Max rows per query (1-10000)
DB_QUERY_READ_ONLY=true          # Only allow SELECT queries
DB_QUERY_TIMEOUT=30.0            # Query timeout in seconds (5-120)
DB_QUERY_POOL_SIZE=5             # Connection pool size (1-20)
DB_QUERY_MAX_OVERFLOW=10         # Max overflow connections (0-50)
```

### Adapter Configuration

```python
adapter = DatabaseQueryAdapter(
    tenant_id="tenant-123",      # Multi-tenant identifier
    max_rows=1000,               # Max rows to fetch (hard limit: 10000)
    read_only=True,              # Security: prevent modifications
    timeout=30.0,                # Query timeout in seconds
    pool_size=5,                 # Connection pool size
    max_overflow=10              # Overflow connections
)
```

---

## Security

### Read-Only Mode (Default)

By default, the adapter operates in **read-only mode** to prevent accidental data modifications:

```python
adapter = DatabaseQueryAdapter(read_only=True)  # Default

# ✅ ALLOWED
await adapter.fetch(
    connection_string="postgresql://localhost/db",
    query="SELECT * FROM users WHERE active = true"
)

# ❌ BLOCKED
await adapter.fetch(
    connection_string="postgresql://localhost/db",
    query="DELETE FROM users WHERE id = 123"
)
# Raises ValidationError: "Only SELECT queries allowed in read-only mode"
```

### Dangerous Keywords Blocked

The following SQL keywords are **automatically blocked** in read-only mode:

- `DROP` - Delete tables/databases
- `DELETE` - Remove rows
- `INSERT` - Add new rows
- `UPDATE` - Modify existing rows
- `TRUNCATE` - Remove all rows
- `ALTER` - Modify table structure

```python
# ❌ All of these will raise ValidationError in read-only mode:
queries = [
    "SELECT * FROM users; DROP TABLE users;",
    "DELETE FROM logs WHERE date < NOW()",
    "INSERT INTO audit SELECT * FROM users",
    "UPDATE users SET role = 'admin'",
    "TRUNCATE TABLE sessions",
    "ALTER TABLE users ADD COLUMN hacked TEXT"
]
```

### Parameterized Queries (SQL Injection Prevention)

**Always use parameterized queries** to prevent SQL injection:

```python
# ✅ SAFE: Parameterized query
documents = await adapter.fetch(
    connection_string="postgresql://localhost/db",
    query="SELECT * FROM articles WHERE user_id = :user_id AND status = :status",
    params={
        "user_id": 123,
        "status": "published"
    }
)

# ❌ UNSAFE: String concatenation (DO NOT DO THIS)
user_id = 123
query = f"SELECT * FROM articles WHERE user_id = {user_id}"  # Vulnerable!
```

### Connection String Security

Connection strings are **automatically masked** in logs:

```python
# Your connection string
connection_string = "postgresql://user:MySecretPassword123@localhost/db"

# Logged as
# "postgresql://user:***@localhost/db"
```

---

## Usage Examples

### Example 1: Fetch Blog Articles

```bash
curl -X POST http://localhost:8002/api/v1/jobs \
  -H "Content-Type: application/json" \
  -d '{
    "source": "database_query",
    "tenant_id": "blog-system",
    "connection_string": "postgresql://reader:password@localhost/blog_db",
    "query": "SELECT article_id, headline, body, author FROM articles WHERE published = true ORDER BY created_at DESC LIMIT 100",
    "db_content_column": "body",
    "db_title_column": "headline",
    "db_id_column": "article_id"
  }'
```

### Example 2: Fetch User Support Tickets

```python
from sources.database_query import DatabaseQueryAdapter

adapter = DatabaseQueryAdapter(tenant_id="support-system")

# Fetch recent support tickets
documents = await adapter.fetch(
    connection_string="mysql://support_readonly:pass@localhost/support_db",
    query="""
        SELECT
            ticket_id,
            subject,
            CONCAT(description, '\n\nComments:\n', comments) as full_content,
            created_at
        FROM tickets
        WHERE status = 'open'
        AND created_at > DATE_SUB(NOW(), INTERVAL 7 DAY)
        ORDER BY priority DESC
    """,
    content_column="full_content",
    title_column="subject",
    id_column="ticket_id",
    max_rows=500
)

print(f"Fetched {len(documents)} open tickets")
await adapter.close()
```

### Example 3: Fetch Product Catalog with Parameterized Query

```python
adapter = DatabaseQueryAdapter(tenant_id="ecommerce")

# Fetch products by category (parameterized for security)
documents = await adapter.fetch(
    connection_string="postgresql://readonly:pass@localhost/products_db",
    query="""
        SELECT
            product_id,
            product_name,
            description,
            specifications,
            price,
            category
        FROM products
        WHERE category = :category
        AND in_stock = :in_stock
        AND price <= :max_price
        ORDER BY popularity DESC
    """,
    params={
        "category": "electronics",
        "in_stock": True,
        "max_price": 1000.00
    },
    content_column="description",
    title_column="product_name",
    id_column="product_id"
)

await adapter.close()
```

### Example 4: Fetch Customer Reviews (SQLite)

```python
adapter = DatabaseQueryAdapter(tenant_id="reviews")

# Fetch from local SQLite database
documents = await adapter.fetch(
    connection_string="sqlite:///data/reviews.db",
    query="""
        SELECT
            review_id,
            product_name,
            review_text,
            rating
        FROM customer_reviews
        WHERE rating >= 4
        ORDER BY helpful_votes DESC
        LIMIT 200
    """,
    content_column="review_text",
    title_column="product_name",
    id_column="review_id"
)

await adapter.close()
```

---

## Column Mapping

### Default Column Names

The adapter looks for these column names by default:

- **Content**: `content`, `body`, `text`, `description`, `message`
- **Title**: `title`
- **ID**: `id`

### Custom Column Mapping

Specify custom columns for your database schema:

```python
documents = await adapter.fetch(
    connection_string="postgresql://localhost/db",
    query="SELECT article_id, headline, full_text FROM articles",
    content_column="full_text",    # Map content to 'full_text' column
    title_column="headline",        # Map title to 'headline' column
    id_column="article_id"          # Map ID to 'article_id' column
)
```

### Fallback to JSON

If no content column is found, the adapter **serializes the entire row as JSON**:

```python
# Query returns: {"id": 1, "name": "John", "email": "john@example.com"}
# Content will be:
# {
#   "id": 1,
#   "name": "John",
#   "email": "john@example.com"
# }
```

---

## Parameterized Queries

### Why Use Parameters?

**NEVER concatenate user input into SQL queries**. Always use parameters to prevent SQL injection:

```python
# ❌ VULNERABLE to SQL injection
user_input = "1 OR 1=1"
query = f"SELECT * FROM users WHERE id = {user_input}"  # DON'T DO THIS!

# ✅ SAFE: Parameterized query
query = "SELECT * FROM users WHERE id = :user_id"
params = {"user_id": user_input}  # Safely bound as parameter
```

### Parameter Syntax

**Named parameters** use `:param_name` syntax:

```python
documents = await adapter.fetch(
    connection_string="postgresql://localhost/db",
    query="""
        SELECT id, title, content
        FROM articles
        WHERE
            author_id = :author_id
            AND category = :category
            AND published_date >= :start_date
            AND published_date <= :end_date
        ORDER BY published_date DESC
    """,
    params={
        "author_id": 42,
        "category": "technology",
        "start_date": "2024-01-01",
        "end_date": "2024-12-31"
    }
)
```

---

## Error Handling

### Common Errors

#### 1. Connection Errors

```python
try:
    documents = await adapter.fetch(
        connection_string="postgresql://invalid_host/db",
        query="SELECT * FROM users"
    )
except FetchError as e:
    print(f"Connection failed: {e}")
    # Output: "Failed to create database engine: could not connect to server"
```

#### 2. Query Timeout

```python
try:
    # Query takes longer than timeout (30 seconds)
    documents = await adapter.fetch(
        connection_string="postgresql://localhost/db",
        query="SELECT * FROM massive_table"
    )
except FetchError as e:
    print(f"Query timed out: {e}")
    # Output: "Query timeout after 30s"
```

#### 3. Validation Errors

```python
try:
    documents = await adapter.fetch(
        connection_string="postgresql://localhost/db",
        query="DELETE FROM users WHERE id = 1"  # Not allowed in read-only mode
    )
except ValidationError as e:
    print(f"Validation failed: {e}")
    # Output: "Only SELECT queries allowed in read-only mode"
```

### Error Handling Best Practices

```python
from sources.database_query import DatabaseQueryAdapter
from sources.base import FetchError, ValidationError

adapter = DatabaseQueryAdapter(tenant_id="tenant-123")

try:
    documents = await adapter.fetch(
        connection_string="postgresql://localhost/db",
        query="SELECT id, title, content FROM articles",
        max_rows=100
    )

    print(f"✅ Successfully fetched {len(documents)} documents")

except ValidationError as e:
    # Input validation failed (bad query, missing params, etc.)
    print(f"❌ Validation error: {e}")
    # Handle: fix query or parameters

except FetchError as e:
    # Database operation failed (connection, timeout, etc.)
    print(f"❌ Fetch error: {e}")
    # Handle: retry, fallback, alert

except Exception as e:
    # Unexpected error
    print(f"❌ Unexpected error: {e}")
    # Handle: log, alert

finally:
    # Always cleanup
    await adapter.close()
```

---

## Best Practices

### 1. Use Read-Only Database Accounts

Create dedicated read-only database users for Rake:

```sql
-- PostgreSQL
CREATE USER rake_readonly WITH PASSWORD 'secure_password';
GRANT CONNECT ON DATABASE mydb TO rake_readonly;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO rake_readonly;

-- MySQL
CREATE USER 'rake_readonly'@'%' IDENTIFIED BY 'secure_password';
GRANT SELECT ON mydb.* TO 'rake_readonly'@'%';

-- SQLite (file permissions)
chmod 444 /path/to/database.db  # Read-only
```

### 2. Optimize Queries

Add `WHERE` clauses and `LIMIT` to reduce data fetching:

```sql
-- ✅ GOOD: Filtered and limited
SELECT id, title, content
FROM articles
WHERE published = true
AND created_at > NOW() - INTERVAL '30 days'
ORDER BY created_at DESC
LIMIT 100

-- ❌ BAD: Fetches entire table
SELECT * FROM articles
```

### 3. Use Indexes

Ensure your database has indexes on filtered columns:

```sql
-- PostgreSQL/MySQL
CREATE INDEX idx_articles_published ON articles(published, created_at);

-- Speeds up queries like:
-- SELECT * FROM articles WHERE published = true ORDER BY created_at DESC
```

### 4. Monitor Query Performance

```python
import time

start = time.time()
documents = await adapter.fetch(
    connection_string="postgresql://localhost/db",
    query="SELECT * FROM articles WHERE published = true",
    max_rows=100
)
duration = time.time() - start

print(f"Fetched {len(documents)} documents in {duration:.2f}s")
```

### 5. Use Connection Pooling

The adapter automatically pools connections. **Reuse the adapter instance**:

```python
# ✅ GOOD: Reuse adapter (connection pooling)
adapter = DatabaseQueryAdapter(tenant_id="tenant-123")

for category in ["tech", "business", "sports"]:
    documents = await adapter.fetch(
        connection_string="postgresql://localhost/db",
        query="SELECT * FROM articles WHERE category = :category",
        params={"category": category}
    )
    # Connection is reused from pool

await adapter.close()

# ❌ BAD: Create new adapter each time (no pooling)
for category in ["tech", "business", "sports"]:
    adapter = DatabaseQueryAdapter()  # New adapter each time
    documents = await adapter.fetch(...)
    await adapter.close()
```

### 6. Cleanup Resources

**Always close the adapter** when done:

```python
adapter = DatabaseQueryAdapter()

try:
    documents = await adapter.fetch(...)
finally:
    await adapter.close()  # Cleanup connections
```

---

## Troubleshooting

### Issue: "connection_string is required"

**Cause**: Missing connection string parameter

**Solution**: Provide a valid connection string

```python
# ❌ Missing connection string
await adapter.fetch(query="SELECT * FROM users")

# ✅ Provide connection string
await adapter.fetch(
    connection_string="postgresql://localhost/db",
    query="SELECT * FROM users"
)
```

### Issue: "Only SELECT queries allowed in read-only mode"

**Cause**: Attempted to run non-SELECT query in read-only mode

**Solution**: Use SELECT queries only, or disable read-only mode (not recommended)

```python
# ✅ Option 1: Use SELECT (recommended)
query = "SELECT * FROM users WHERE active = true"

# ⚠️ Option 2: Disable read-only (use with caution)
adapter = DatabaseQueryAdapter(read_only=False)
```

### Issue: "Query timeout after 30s"

**Cause**: Query takes longer than configured timeout

**Solution**: Optimize query or increase timeout

```python
# Option 1: Optimize query (add indexes, WHERE clauses, LIMIT)
query = "SELECT * FROM articles WHERE published = true LIMIT 100"

# Option 2: Increase timeout
adapter = DatabaseQueryAdapter(timeout=120.0)  # 2 minutes
```

### Issue: "Failed to create database engine"

**Cause**: Invalid connection string or database unreachable

**Solution**: Verify connection string and database availability

```python
# Check connection string format
postgresql://user:password@host:port/database
mysql://user:password@host:port/database
sqlite:///absolute/path/to/database.db

# Test connection manually
psql -h localhost -U user -d database  # PostgreSQL
mysql -h localhost -u user -p database  # MySQL
sqlite3 /path/to/database.db            # SQLite
```

### Issue: "Reached max_rows limit"

**Cause**: Query returns more rows than configured limit

**Solution**: Adjust query or increase max_rows

```python
# Option 1: Add LIMIT to query
query = "SELECT * FROM articles ORDER BY created_at DESC LIMIT 100"

# Option 2: Increase max_rows (up to 10000)
documents = await adapter.fetch(
    connection_string="postgresql://localhost/db",
    query="SELECT * FROM articles",
    max_rows=5000  # Override default
)
```

---

## Pipeline Integration

Database query documents flow through the complete 5-stage pipeline:

1. **FETCH** (Database Query) → Query database, convert rows to documents
2. **CLEAN** → Extract clean text, remove noise
3. **CHUNK** → Split into chunks (500 tokens, 50 overlap)
4. **EMBED** → Generate embeddings (OpenAI text-embedding-3-small)
5. **STORE** → Store in DataForge vector database

### Full Pipeline Example

```bash
curl -X POST http://localhost:8002/api/v1/jobs \
  -H "Content-Type: application/json" \
  -d '{
    "source": "database_query",
    "tenant_id": "tenant-123",
    "connection_string": "postgresql://readonly:pass@localhost/mydb",
    "query": "SELECT id, title, content FROM articles WHERE published = true LIMIT 100",
    "db_content_column": "content",
    "db_title_column": "title",
    "db_id_column": "id"
  }'

# Returns job_id for tracking
# {
#   "job_id": "job-abc123def456",
#   "status": "pending",
#   "source": "database_query"
# }

# Check job status
curl http://localhost:8002/api/v1/jobs/job-abc123def456

# When complete:
# {
#   "job_id": "job-abc123def456",
#   "status": "completed",
#   "documents_stored": 100,
#   "chunks_created": 423,
#   "embeddings_generated": 423
# }
```

---

## Summary

The Database Query Adapter provides:

- ✅ **Security-First Design**: Read-only mode, query validation, SQL injection prevention
- ✅ **Multi-Database Support**: PostgreSQL, MySQL, SQLite
- ✅ **Production-Ready**: Connection pooling, timeouts, error handling
- ✅ **Flexible**: Column mapping, parameterized queries, row limits
- ✅ **Fully Integrated**: Complete pipeline support (CLEAN → CHUNK → EMBED → STORE)

For questions or issues, refer to the main [Rake README](../README.md) or open an issue on GitHub.
