# URL Scraping Integration Guide

Complete guide for scraping web content including single pages, bulk sitemaps, and content extraction.

---

## Overview

The URL Scrape adapter allows Rake to automatically fetch and process content from web pages, articles, documentation sites, and blogs. It features intelligent content extraction, robots.txt compliance, and rate limiting.

**Supported content types:**
- **Web Pages**: Articles, blog posts, documentation
- **News Sites**: News articles and press releases
- **Documentation**: Technical documentation and guides
- **Blogs**: Individual posts and article archives
- **Marketing Pages**: Product pages and landing pages

**Key Features:**
- ✅ Single URL fetching
- ✅ Sitemap bulk processing
- ✅ Robots.txt compliance
- ✅ Intelligent content extraction
- ✅ Metadata extraction (title, description, author, etc.)
- ✅ Rate limiting per domain
- ✅ Content size limits
- ✅ Timeout protection

---

## Configuration

### Required Settings

Add these to your `.env` file:

```bash
# URL Scraping Configuration
URL_SCRAPE_USER_AGENT="Rake/1.0 (Data Ingestion Bot)"
URL_SCRAPE_RATE_LIMIT=1.0  # 1 second between requests
URL_SCRAPE_MAX_SIZE=10485760  # 10MB max content size
URL_SCRAPE_TIMEOUT=30.0  # 30 seconds timeout
URL_SCRAPE_RESPECT_ROBOTS=true  # Honor robots.txt
```

### Configuration Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `URL_SCRAPE_USER_AGENT` | "Rake/1.0 (Data Ingestion Bot)" | User-Agent header for requests |
| `URL_SCRAPE_RATE_LIMIT` | 1.0 | Delay between requests (seconds) |
| `URL_SCRAPE_MAX_SIZE` | 10MB | Maximum content size to fetch |
| `URL_SCRAPE_TIMEOUT` | 30.0 | Request timeout (seconds) |
| `URL_SCRAPE_RESPECT_ROBOTS` | true | Honor robots.txt rules |

---

## Usage

### 1. Submit Job via API

**Fetch a single URL:**

```bash
curl -X POST http://localhost:8002/api/v1/jobs \
  -H "Content-Type: application/json" \
  -d '{
    "source": "url_scrape",
    "url": "https://example.com/article",
    "tenant_id": "tenant-123"
  }'
```

**Fetch multiple URLs from sitemap:**

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

**Fetch with custom metadata:**

```bash
curl -X POST http://localhost:8002/api/v1/jobs \
  -H "Content-Type: application/json" \
  -d '{
    "source": "url_scrape",
    "url": "https://blog.example.com/post-123",
    "tenant_id": "tenant-123",
    "metadata": {
      "category": "blog",
      "source_site": "Example Blog",
      "analyst": "John Doe"
    }
  }'
```

### 2. Python SDK Usage

```python
from sources.url_scrape import URLScrapeAdapter

# Initialize adapter
adapter = URLScrapeAdapter(
    user_agent="MyBot/1.0 (Custom Scraper)",
    tenant_id="tenant-123",
    rate_limit_delay=1.5,  # 1.5 seconds between requests
    respect_robots=True
)

# Fetch single URL
documents = await adapter.fetch(
    url="https://example.com/article"
)

# Fetch from sitemap
documents = await adapter.fetch(
    sitemap_url="https://example.com/sitemap.xml",
    max_pages=20
)

# Access document data
for doc in documents:
    print(f"Title: {doc.metadata.get('title')}")
    print(f"URL: {doc.metadata['url']}")
    print(f"Description: {doc.metadata.get('description')}")
    print(f"Content length: {len(doc.content)} chars")
    print(f"Fetched at: {doc.metadata['fetched_at']}")
```

---

## API Parameters

### Request Schema

```json
{
  "source": "url_scrape",               // Required
  "url": "https://example.com/page",    // Either url OR sitemap_url required
  "sitemap_url": "https://example.com/sitemap.xml",  // Either url OR sitemap_url required
  "max_pages": 10,                      // Optional (default: 10, max: 100)
  "tenant_id": "tenant-123",            // Optional
  "metadata": {                          // Optional additional metadata
    "category": "documentation",
    "project": "Product Docs"
  }
}
```

### Parameters

| Parameter | Required | Type | Description |
|-----------|----------|------|-------------|
| `source` | Yes | string | Must be "url_scrape" |
| `url` | Conditional | string | Single URL to scrape |
| `sitemap_url` | Conditional | string | URL of XML sitemap for bulk scraping |
| `max_pages` | No | integer | Max URLs to fetch from sitemap (1-100, default: 10) |
| `tenant_id` | No | string | Multi-tenant identifier |
| `metadata` | No | object | Additional metadata to attach |

**Note:** You must provide either `url` OR `sitemap_url`, but not both.

---

## Content Extraction

The URL scraper uses intelligent content extraction to identify the main content:

### 1. Semantic HTML Tags

Prioritizes semantic HTML5 tags:
```html
<!-- Highest priority -->
<article>Main article content</article>

<!-- Second priority -->
<main>Main page content</main>

<!-- Third priority -->
<div role="main">Content with ARIA role</div>
```

### 2. Common Content Classes

Looks for common content container classes:
```html
<div class="content">...</div>
<div class="main-content">...</div>
<div class="post-content">...</div>
<div class="article-body">...</div>
```

### 3. Fallback to Body

If no semantic tags found, extracts all body text excluding:
- Navigation (`<nav>`)
- Headers (`<header>`)
- Footers (`<footer>`)
- Sidebars (`<aside>`)
- Scripts and styles

---

## Metadata Extraction

### Standard Meta Tags

```html
<head>
  <title>Article Title</title>
  <meta name="description" content="Article description">
  <meta name="author" content="John Doe">
  <meta name="keywords" content="tech, tutorial, guide">
  <meta name="published" content="2023-12-01">
</head>
```

**Extracted as:**
```python
{
    "title": "Article Title",
    "description": "Article description",
    "author": "John Doe",
    "keywords": "tech, tutorial, guide",
    "published": "2023-12-01"
}
```

### Open Graph Tags

```html
<meta property="og:title" content="OG Title">
<meta property="og:description" content="OG Description">
<meta property="og:image" content="https://example.com/image.jpg">
<meta property="og:type" content="article">
<meta property="og:url" content="https://example.com/canonical">
<meta property="og:site_name" content="Example Site">
```

**Extracted as:**
```python
{
    "og_title": "OG Title",
    "og_description": "OG Description",
    "og_image": "https://example.com/image.jpg",
    "og_type": "article",
    "og_url": "https://example.com/canonical",
    "og_site_name": "Example Site"
}
```

### Twitter Card Tags

```html
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="Twitter Title">
<meta name="twitter:description" content="Twitter Description">
<meta name="twitter:image" content="https://example.com/twitter.jpg">
```

**Extracted as:**
```python
{
    "twitter_card": "summary_large_image",
    "twitter_title": "Twitter Title",
    "twitter_description": "Twitter Description",
    "twitter_image": "https://example.com/twitter.jpg"
}
```

---

## Robots.txt Compliance

The URL scraper respects robots.txt by default:

### How It Works

1. **Fetches robots.txt**: `https://example.com/robots.txt`
2. **Parses rules**: Identifies allowed/disallowed paths
3. **Checks URL**: Validates URL against rules
4. **Honors decision**: Blocks crawling if disallowed

### Example robots.txt

```
# Allowed
User-agent: *
Disallow: /admin/
Disallow: /private/
Allow: /

# This allows: https://example.com/article
# This blocks: https://example.com/admin/settings
```

### Disabling Robots.txt Check

```python
# For testing or authorized scraping
adapter = URLScrapeAdapter(
    tenant_id="tenant-123",
    respect_robots=False  # Disable robots.txt checking
)
```

---

## Sitemap Processing

### XML Sitemap Format

```xml
<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url>
    <loc>https://example.com/page1</loc>
    <lastmod>2023-12-01</lastmod>
    <priority>0.8</priority>
  </url>
  <url>
    <loc>https://example.com/page2</loc>
    <lastmod>2023-12-02</lastmod>
    <priority>0.5</priority>
  </url>
</urlset>
```

### Sitemap Index Support

```xml
<?xml version="1.0" encoding="UTF-8"?>
<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <sitemap>
    <loc>https://example.com/sitemap-articles.xml</loc>
    <lastmod>2023-12-01</lastmod>
  </sitemap>
  <sitemap>
    <loc>https://example.com/sitemap-blog.xml</loc>
    <lastmod>2023-12-02</lastmod>
  </sitemap>
</sitemapindex>
```

The adapter automatically:
- Detects sitemap indexes
- Fetches all child sitemaps
- Extracts URLs from all sitemaps
- Respects `max_pages` limit across all sitemaps

---

## Rate Limiting

### Per-Domain Rate Limiting

Rate limiting is applied **per domain** to be respectful:

```python
# 1 second delay between requests to same domain
adapter = URLScrapeAdapter(
    tenant_id="tenant-123",
    rate_limit_delay=1.0  # 1 request per second
)

# More conservative (every 2 seconds)
adapter = URLScrapeAdapter(
    tenant_id="tenant-123",
    rate_limit_delay=2.0  # 1 request every 2 seconds
)
```

### Best Practices

| Website Type | Recommended Delay |
|--------------|-------------------|
| Small sites | 2-3 seconds |
| Medium sites | 1-2 seconds |
| Large CDNs | 0.5-1 second |
| News sites | 1-2 seconds |
| Documentation | 1 second |

**Important**: Always respect website terms of service and robots.txt rules.

---

## Error Handling

### Common Errors

**1. URL Blocked by robots.txt:**

```
FetchError: URL https://example.com/admin is disallowed by robots.txt
```

**Solution:** Either respect the block or disable robots.txt checking (only if authorized)

---

**2. Invalid URL:**

```
ValidationError: Invalid URL format: not-a-valid-url
```

**Solution:** Ensure URL starts with `http://` or `https://`

---

**3. Content Too Large:**

```
FetchError: Content size (15728640 bytes) exceeds maximum (10485760 bytes)
```

**Solution:** Increase max size or skip large pages:
```python
adapter = URLScrapeAdapter(
    max_content_size=20 * 1024 * 1024  # 20MB
)
```

---

**4. Request Timeout:**

```
FetchError: Request timeout after 30.0 seconds
```

**Solution:** Increase timeout:
```python
adapter = URLScrapeAdapter(timeout=60.0)  # 60 seconds
```

---

**5. Non-HTML Content:**

```
FetchError: Content type application/pdf is not HTML
```

**Solution:** URL scraper only handles HTML. Use file upload for PDFs.

---

**6. HTTP Error:**

```
FetchError: HTTP 404: Not Found
FetchError: HTTP 500: Internal Server Error
```

**Solution:** Verify URL is accessible and try again later

---

## Advanced Usage

### Batch Processing Multiple Sites

```python
urls = [
    "https://blog.example.com/post-1",
    "https://blog.example.com/post-2",
    "https://news.example.com/article-1",
    "https://docs.example.com/guide",
]

for url in urls:
    response = await client.post(
        "/api/v1/jobs",
        json={
            "source": "url_scrape",
            "url": url,
            "tenant_id": "tenant-123"
        }
    )
    job_id = response.json()["job_id"]
    print(f"Submitted job {job_id} for {url}")

    # Rate limiting between submissions
    await asyncio.sleep(1.0)
```

### Scheduled Scraping

```python
from scheduler import RakeScheduler

scheduler = RakeScheduler()

# Scrape blog daily at 9 AM
scheduler.add_job(
    job_id="blog-scrape-daily",
    source="url_scrape",
    tenant_id="tenant-123",
    cron_expression="0 9 * * *",  # 9 AM daily
    sitemap_url="https://blog.example.com/sitemap.xml",
    max_pages=20
)
```

### Custom User-Agent

```python
# Identify your bot clearly
adapter = URLScrapeAdapter(
    user_agent="MyCompany Research Bot/1.0 (+https://mycompany.com/bot)",
    tenant_id="tenant-123"
)
```

### Filtering Sitemap URLs

```python
# Fetch sitemap and filter URLs manually
adapter = URLScrapeAdapter(tenant_id="tenant-123")

# Get all URLs from sitemap
all_urls = await adapter._parse_sitemap(
    "https://example.com/sitemap.xml",
    max_pages=100
)

# Filter for specific paths
blog_urls = [url for url in all_urls if "/blog/" in url]
doc_urls = [url for url in all_urls if "/docs/" in url]

# Fetch only blog posts
for url in blog_urls[:10]:  # Limit to 10
    documents = await adapter.fetch(url=url)
    # Process documents
```

---

## Pipeline Processing

After fetching, URL scraped documents go through the full 5-stage pipeline:

1. **FETCH**: Retrieved from web URL ✓
2. **CLEAN**: HTML removed, text normalized
3. **CHUNK**: Split into semantic segments
4. **EMBED**: Vector embeddings generated (OpenAI)
5. **STORE**: Persisted to DataForge (PostgreSQL + pgvector)

**Queryable metadata in DataForge:**
- URL, title, description, author
- Publication date, keywords
- Open Graph metadata
- Full-text search on content
- Vector similarity search

---

## Best Practices

### 1. Always Set User-Agent

```python
# Good - Identifies your bot
adapter = URLScrapeAdapter(
    user_agent="MyBot/1.0 (+https://example.com/bot-info)"
)

# Bad - Generic agent may be blocked
adapter = URLScrapeAdapter(user_agent="Mozilla/5.0...")
```

### 2. Respect Robots.txt

```python
# Default - respects robots.txt
adapter = URLScrapeAdapter(respect_robots=True)

# Only disable if you have explicit permission
adapter = URLScrapeAdapter(respect_robots=False)
```

### 3. Use Appropriate Rate Limiting

```python
# Good - 1-2 second delay
adapter = URLScrapeAdapter(rate_limit_delay=1.5)

# Bad - Too aggressive
adapter = URLScrapeAdapter(rate_limit_delay=0.1)
```

### 4. Limit Sitemap Processing

```python
# Good - Reasonable limit
documents = await adapter.fetch(
    sitemap_url="https://example.com/sitemap.xml",
    max_pages=20
)

# Bad - May overwhelm server
documents = await adapter.fetch(
    sitemap_url="https://example.com/sitemap.xml",
    max_pages=1000
)
```

### 5. Handle Errors Gracefully

```python
try:
    documents = await adapter.fetch(url="https://example.com/page")
except FetchError as e:
    logger.error(f"Failed to fetch {url}: {e}")
    # Continue with next URL
except ValidationError as e:
    logger.error(f"Invalid input: {e}")
    # Fix input and retry
```

### 6. Cache Results

Once scraped, content is in DataForge. Query DataForge instead of re-scraping:

```python
# First time - scrapes from web
await adapter.fetch(url="https://blog.example.com/post-1")

# Later - query DataForge
results = dataforge.search(
    query="product launch",
    filters={"url": "https://blog.example.com/post-1"}
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
- Robots.txt checking
- Content extraction
- Metadata parsing
- Rate limiting delays

### Health Check

Test URL scraper connectivity:

```python
adapter = URLScrapeAdapter(tenant_id="tenant-123")

is_healthy = await adapter.health_check()
if not is_healthy:
    print("URL scraper HTTP client is not working")
```

### Verify Configuration

```python
from config import settings

print(f"User-Agent: {settings.URL_SCRAPE_USER_AGENT}")
print(f"Rate Limit: {settings.URL_SCRAPE_RATE_LIMIT}")
print(f"Max Size: {settings.URL_SCRAPE_MAX_SIZE}")
print(f"Timeout: {settings.URL_SCRAPE_TIMEOUT}")
print(f"Respect Robots: {settings.URL_SCRAPE_RESPECT_ROBOTS}")
```

### Test Single URL First

Before bulk scraping, test with a single URL:

```bash
curl -X POST http://localhost:8002/api/v1/jobs \
  -H "Content-Type: application/json" \
  -d '{
    "source": "url_scrape",
    "url": "https://example.com/test-page",
    "tenant_id": "test"
  }'
```

### Check Website Accessibility

```bash
# Test if website is accessible
curl -I https://example.com

# Check robots.txt
curl https://example.com/robots.txt

# Check sitemap
curl https://example.com/sitemap.xml
```

---

## Ethical Web Scraping

### Legal Compliance

- ✅ Read and comply with website Terms of Service
- ✅ Respect robots.txt directives
- ✅ Honor rate limiting requests
- ✅ Identify your bot clearly in User-Agent
- ✅ Don't scrape personal or sensitive data
- ✅ Cache results to minimize requests

### Respectful Practices

- ✅ Use reasonable rate limits (1-2 seconds)
- ✅ Scrape during off-peak hours
- ✅ Don't overwhelm small websites
- ✅ Provide contact information
- ✅ Stop if requested by website owner
- ✅ Don't circumvent access controls

### When NOT to Scrape

- ❌ Websites with "no scraping" in TOS
- ❌ Login-protected content
- ❌ Paywalled content
- ❌ Personal information
- ❌ Copyrighted content (without permission)
- ❌ Data protected by anti-scraping measures

---

## Resources

- **Robots.txt**: https://www.robotstxt.org/
- **Sitemaps Protocol**: https://www.sitemaps.org/
- **Open Graph**: https://ogp.me/
- **Twitter Cards**: https://developer.twitter.com/en/docs/twitter-for-websites/cards/
- **Web Scraping Ethics**: https://www.scraperapi.com/blog/web-scraping-ethics/

---

## Support

For issues with URL scraping:

1. Check logs with correlation ID
2. Verify URL is accessible
3. Test robots.txt compliance
4. Review rate limit settings
5. Check content size and timeout

**Status**: ✅ URL Scraping Integration Complete
