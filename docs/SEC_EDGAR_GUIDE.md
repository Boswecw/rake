# SEC EDGAR Integration Guide

Complete guide for fetching financial filings from the SEC EDGAR database using Rake.

---

## Overview

The SEC EDGAR (Electronic Data Gathering, Analysis, and Retrieval) adapter allows Rake to automatically fetch and process financial filings from the U.S. Securities and Exchange Commission database.

**Supported filing types:**
- **10-K**: Annual reports
- **10-Q**: Quarterly reports
- **8-K**: Current reports (material events)
- **DEF 14A**: Proxy statements
- **S-1, S-3**: Registration statements
- **13F-HR**: Institutional investment reports
- **13D, 13G**: Beneficial ownership reports
- **3, 4, 5**: Insider trading reports
- **20-F, 6-K**: Foreign issuer filings
- And many more

---

## Configuration

### Required Settings

Add these to your `.env` file:

```bash
# SEC EDGAR Configuration
SEC_EDGAR_USER_AGENT="YourCompany/1.0 contact@yourcompany.com"
SEC_EDGAR_RATE_LIMIT=0.1  # 10 requests/second (default)
```

**Important:** The SEC requires a User-Agent string that includes:
- Your company/application name
- A contact email address OR website URL

**Example valid User-Agent strings:**
```
"MyFinanceApp/2.0 support@mycompany.com"
"Research Project/1.0 researcher@university.edu"
"FinancialAnalysis/3.5 https://myapp.com"
"InvestmentTool/1.0 contact@trading.com"
```

---

## Usage

### 1. Submit Job via API

**Fetch latest 10-K for Apple:**

```bash
curl -X POST http://localhost:8002/api/v1/jobs \
  -H "Content-Type: application/json" \
  -d '{
    "source": "sec_edgar",
    "ticker": "AAPL",
    "form_type": "10-K",
    "count": 1,
    "tenant_id": "tenant-123"
  }'
```

**Fetch multiple quarterly reports by CIK:**

```bash
curl -X POST http://localhost:8002/api/v1/jobs \
  -H "Content-Type: application/json" \
  -d '{
    "source": "sec_edgar",
    "cik": "0000320193",
    "form_type": "10-Q",
    "count": 3,
    "tenant_id": "tenant-123"
  }'
```

**Fetch all recent filings (no form type filter):**

```bash
curl -X POST http://localhost:8002/api/v1/jobs \
  -H "Content-Type: application/json" \
  -d '{
    "source": "sec_edgar",
    "ticker": "MSFT",
    "count": 5,
    "tenant_id": "tenant-123"
  }'
```

### 2. Python SDK Usage

```python
from sources.sec_edgar import SECEdgarAdapter

# Initialize adapter
adapter = SECEdgarAdapter(
    user_agent="MyApp/1.0 admin@example.com",
    tenant_id="tenant-123",
    rate_limit_delay=0.1  # 10 req/s max
)

# Fetch by ticker symbol
documents = await adapter.fetch(
    ticker="AAPL",
    form_type="10-K",
    count=1
)

# Fetch by CIK number
documents = await adapter.fetch(
    cik="0000320193",
    form_type="10-Q",
    count=3
)

# Access document data
for doc in documents:
    print(f"Company: {doc.metadata['company_name']}")
    print(f"Filing: {doc.metadata['form_type']}")
    print(f"Date: {doc.metadata['filing_date']}")
    print(f"URL: {doc.metadata['filing_url']}")
    print(f"Content: {doc.content[:500]}...")
```

---

## API Parameters

### Request Schema

```json
{
  "source": "sec_edgar",           // Required
  "ticker": "AAPL",                // Either ticker OR cik required
  "cik": "0000320193",             // Either ticker OR cik required
  "form_type": "10-K",             // Optional (filters by form type)
  "count": 1,                      // Optional (default: 1, max: 10)
  "tenant_id": "tenant-123",       // Optional
  "metadata": {                     // Optional additional metadata
    "analyst": "John Doe",
    "project": "Q4 Analysis"
  }
}
```

### Parameters

| Parameter | Required | Type | Description |
|-----------|----------|------|-------------|
| `source` | Yes | string | Must be "sec_edgar" |
| `ticker` | Conditional | string | Stock ticker symbol (e.g., "AAPL", "MSFT") |
| `cik` | Conditional | string | Company CIK number (e.g., "0000320193") |
| `form_type` | No | string | Filing form type (e.g., "10-K", "10-Q") |
| `count` | No | integer | Number of filings to fetch (1-10, default: 1) |
| `tenant_id` | No | string | Multi-tenant identifier |
| `metadata` | No | object | Additional metadata to attach |

**Note:** You must provide either `ticker` OR `cik`, but not necessarily both.

---

## Finding Company Information

### Find CIK from Ticker

The adapter automatically converts ticker symbols to CIK numbers:

```bash
# Using ticker - adapter converts to CIK automatically
curl -X POST http://localhost:8002/api/v1/jobs \
  -H "Content-Type: application/json" \
  -d '{
    "source": "sec_edgar",
    "ticker": "GOOGL",
    "form_type": "10-K",
    "count": 1
  }'
```

### Find CIK Manually

1. **SEC EDGAR Search**: https://www.sec.gov/edgar/searchedgar/companysearch.html
2. Search by company name or ticker
3. Copy the CIK number from results

**Example CIK numbers:**
- Apple Inc.: `0000320193`
- Microsoft Corp.: `0000789019`
- Amazon.com Inc.: `0001018724`
- Tesla Inc.: `0001318605`

---

## Document Metadata

Each fetched filing includes comprehensive metadata:

```python
{
    "company_name": "APPLE INC",
    "cik": "0000320193",
    "form_type": "10-K",
    "filing_date": "2023-11-03",
    "accession_number": "0000320193-23-000077",
    "file_number": "001-36743",
    "filing_url": "https://www.sec.gov/Archives/edgar/data/...",
    "filename": "10-K Annual Report",
    "fetched_at": "2023-12-03T10:30:00Z",
    "tenant_id": "tenant-123"
}
```

---

## Rate Limiting

The SEC enforces a **10 requests per second** limit for fair access. Rake automatically handles rate limiting:

```python
# Default configuration (10 req/s)
adapter = SECEdgarAdapter(
    user_agent="MyApp admin@example.com",
    rate_limit_delay=0.1  # 10 requests/second
)

# More conservative (5 req/s)
adapter = SECEdgarAdapter(
    user_agent="MyApp admin@example.com",
    rate_limit_delay=0.2  # 5 requests/second
)
```

**SEC Fair Access Guidelines:**
- Maximum 10 requests per second
- Must include contact information in User-Agent
- Respect HTTP error codes and retry policies
- Cache responses when appropriate

---

## Error Handling

### Common Errors

**1. Missing User-Agent Configuration:**

```
ValidationError: SEC_EDGAR_USER_AGENT configuration is required for SEC EDGAR source
```

**Solution:** Set `SEC_EDGAR_USER_AGENT` in `.env` file

---

**2. Invalid User-Agent Format:**

```
ValidationError: User-Agent must include contact information (email or website)
```

**Solution:** Include email or website in user-agent:
```bash
SEC_EDGAR_USER_AGENT="MyApp/1.0 contact@example.com"
```

---

**3. Ticker Not Found:**

```
FetchError: Ticker 'INVALID' not found in SEC EDGAR
```

**Solution:** Verify ticker symbol or use CIK number instead

---

**4. No Filings Found:**

```
FetchError: No filings found for CIK 0000320193
```

**Solution:** Check if company has filed documents, or adjust `form_type` filter

---

**5. Rate Limit Exceeded:**

```
HTTPError: 429 Too Many Requests
```

**Solution:** Rake automatically handles rate limiting, but if you encounter this:
- Increase `SEC_EDGAR_RATE_LIMIT` (e.g., 0.15 for ~6.7 req/s)
- Reduce concurrent requests
- Add delay between job submissions

---

## Advanced Usage

### Scheduled Jobs

Automatically fetch new filings daily:

```python
from scheduler import RakeScheduler

scheduler = RakeScheduler()

# Fetch Apple's latest 10-Q every weekday at 6 PM ET
scheduler.add_job(
    job_id="apple-10q-daily",
    source="sec_edgar",
    tenant_id="tenant-123",
    cron_expression="0 18 * * MON-FRI",  # 6 PM weekdays
    ticker="AAPL",
    form_type="10-Q",
    count=1
)
```

### Batch Processing Multiple Companies

```python
companies = [
    {"ticker": "AAPL", "name": "Apple"},
    {"ticker": "MSFT", "name": "Microsoft"},
    {"ticker": "GOOGL", "name": "Google"},
    {"ticker": "AMZN", "name": "Amazon"},
]

for company in companies:
    response = await client.post(
        "/api/v1/jobs",
        json={
            "source": "sec_edgar",
            "ticker": company["ticker"],
            "form_type": "10-K",
            "count": 1,
            "metadata": {"company_name": company["name"]}
        }
    )
    job_id = response.json()["job_id"]
    print(f"Submitted job {job_id} for {company['name']}")

    # Wait to respect rate limits
    await asyncio.sleep(0.15)
```

### Custom Filing Size Limits

```python
# Allow larger filings (default: 50MB)
adapter = SECEdgarAdapter(
    user_agent="MyApp admin@example.com",
    tenant_id="tenant-123",
    max_filing_size=100 * 1024 * 1024  # 100MB
)
```

---

## Pipeline Processing

After fetching, SEC EDGAR documents go through the full 5-stage pipeline:

1. **FETCH**: Retrieved from SEC EDGAR ✓
2. **CLEAN**: HTML removed, text normalized
3. **CHUNK**: Split into semantic segments
4. **EMBED**: Vector embeddings generated (OpenAI)
5. **STORE**: Persisted to DataForge (PostgreSQL + pgvector)

**Queryable metadata in DataForge:**
- Company name, CIK, ticker
- Filing type, date, accession number
- Document URL
- Full-text search on content
- Vector similarity search

---

## Best Practices

### 1. Use CIK for Reliability

CIK numbers are more reliable than ticker symbols:
```python
# Preferred - CIK never changes
{"cik": "0000320193"}

# Alternative - ticker may change
{"ticker": "AAPL"}
```

### 2. Filter by Form Type

Specify form types to reduce processing time:
```python
# Good - specific form type
{"ticker": "AAPL", "form_type": "10-K"}

# Slower - fetches all filings
{"ticker": "AAPL"}
```

### 3. Limit Count for Testing

Start with count=1 for testing:
```python
# Testing
{"ticker": "AAPL", "form_type": "10-K", "count": 1}

# Production
{"ticker": "AAPL", "form_type": "10-K", "count": 5}
```

### 4. Monitor Rate Limits

Check logs for rate limit warnings:
```bash
tail -f logs/rake.log | grep "rate limit"
```

### 5. Cache Frequently Used Filings

Once processed, filings are stored in DataForge. Query DataForge instead of re-fetching:
```python
# First time - fetches from SEC
await adapter.fetch(ticker="AAPL", form_type="10-K", count=1)

# Subsequent queries - use DataForge
results = dataforge.search(
    query="Apple revenue",
    filters={"cik": "0000320193", "form_type": "10-K"}
)
```

---

## Troubleshooting

### Debug Mode

Enable debug logging:

```bash
LOG_LEVEL=DEBUG python main.py
```

Check logs for:
- Ticker → CIK conversion
- Filing list retrieval
- Content extraction
- Rate limiting

### Health Check

Test SEC EDGAR connectivity:

```python
adapter = SECEdgarAdapter(
    user_agent="MyApp admin@example.com",
    tenant_id="tenant-123"
)

is_healthy = await adapter.health_check()
if not is_healthy:
    print("SEC EDGAR is not accessible")
```

### Verify Configuration

```python
from config import settings

print(f"User-Agent: {settings.SEC_EDGAR_USER_AGENT}")
print(f"Rate Limit: {settings.SEC_EDGAR_RATE_LIMIT}")
```

---

## SEC EDGAR Resources

- **SEC EDGAR Homepage**: https://www.sec.gov/edgar
- **Company Search**: https://www.sec.gov/edgar/searchedgar/companysearch.html
- **Filing Types**: https://www.sec.gov/forms
- **Developer Resources**: https://www.sec.gov/developer
- **Fair Access Policy**: https://www.sec.gov/os/accessing-edgar-data

---

## Support

For issues with SEC EDGAR integration:

1. Check logs with correlation ID
2. Verify User-Agent configuration
3. Test health check endpoint
4. Review rate limit settings
5. Consult SEC EDGAR status page

**Status**: ✅ SEC EDGAR Integration Complete
