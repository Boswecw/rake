"""Integration Tests for API Endpoints

Tests for Rake REST API endpoints including job submission,
status retrieval, and listing.

Run with:
    pytest tests/integration/test_api_endpoints.py -v
"""

import pytest
from fastapi.testclient import TestClient


@pytest.mark.integration
class TestHealthEndpoints:
    """Tests for health check endpoints."""

    def test_root_endpoint(self, client):
        """Test root endpoint returns service info."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "rake"
        assert "version" in data

    def test_health_endpoint(self, client):
        """Test health check endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "dependencies" in data

    def test_api_health_endpoint(self, client):
        """Test API-specific health endpoint."""
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "statistics" in data


@pytest.mark.integration
class TestJobSubmission:
    """Tests for job submission endpoint."""

    def test_submit_job_file_upload(self, client, sample_pdf_path):
        """Test submitting a file upload job."""
        response = client.post("/api/v1/jobs", json={
            "source": "file_upload",
            "file_path": str(sample_pdf_path),
            "tenant_id": "tenant-test"
        })

        assert response.status_code == 202
        data = response.json()

        # Verify response structure
        assert "job_id" in data
        assert "correlation_id" in data
        assert data["status"] == "pending"
        assert data["source"] == "file_upload"
        assert data["tenant_id"] == "tenant-test"

    def test_submit_job_missing_file_path(self, client):
        """Test that file_upload source requires file_path."""
        response = client.post("/api/v1/jobs", json={
            "source": "file_upload",
            "tenant_id": "tenant-test"
            # Missing file_path
        })

        assert response.status_code == 400
        assert "file_path" in response.json()["detail"]

    def test_submit_job_url_scrape(self, client):
        """Test submitting a URL scrape job."""
        response = client.post("/api/v1/jobs", json={
            "source": "url_scrape",
            "url": "https://example.com",
            "tenant_id": "tenant-test"
        })

        assert response.status_code == 202
        data = response.json()
        assert data["source"] == "url_scrape"

    def test_submit_job_missing_url(self, client):
        """Test that url_scrape source requires url."""
        response = client.post("/api/v1/jobs", json={
            "source": "url_scrape",
            "tenant_id": "tenant-test"
            # Missing url
        })

        assert response.status_code == 400
        assert "url" in response.json()["detail"]


@pytest.mark.integration
class TestJobRetrieval:
    """Tests for job status retrieval."""

    def test_get_job_by_id(self, client, sample_pdf_path):
        """Test retrieving job by ID."""
        # First submit a job
        submit_response = client.post("/api/v1/jobs", json={
            "source": "file_upload",
            "file_path": str(sample_pdf_path),
            "tenant_id": "tenant-test"
        })
        job_id = submit_response.json()["job_id"]

        # Then retrieve it
        get_response = client.get(f"/api/v1/jobs/{job_id}")
        assert get_response.status_code == 200

        data = get_response.json()
        assert data["job_id"] == job_id
        assert "status" in data
        assert "created_at" in data

    def test_get_nonexistent_job(self, client):
        """Test retrieving a job that doesn't exist."""
        response = client.get("/api/v1/jobs/nonexistent-job-id")
        assert response.status_code == 404


@pytest.mark.integration
class TestJobListing:
    """Tests for job listing endpoint."""

    def test_list_all_jobs(self, client):
        """Test listing all jobs."""
        response = client.get("/api/v1/jobs")
        assert response.status_code == 200

        data = response.json()
        assert "jobs" in data
        assert "total" in data
        assert "page" in data
        assert "page_size" in data

    def test_list_jobs_with_tenant_filter(self, client, sample_pdf_path):
        """Test filtering jobs by tenant_id."""
        # Submit job for tenant
        client.post("/api/v1/jobs", json={
            "source": "file_upload",
            "file_path": str(sample_pdf_path),
            "tenant_id": "tenant-123"
        })

        # List jobs for that tenant
        response = client.get("/api/v1/jobs?tenant_id=tenant-123")
        assert response.status_code == 200

        data = response.json()
        # All jobs should be for tenant-123
        for job in data["jobs"]:
            assert job["tenant_id"] == "tenant-123"

    def test_list_jobs_with_status_filter(self, client, sample_pdf_path):
        """Test filtering jobs by status."""
        # Submit a job (will be pending)
        client.post("/api/v1/jobs", json={
            "source": "file_upload",
            "file_path": str(sample_pdf_path),
            "tenant_id": "tenant-test"
        })

        # List pending jobs
        response = client.get("/api/v1/jobs?status=pending")
        assert response.status_code == 200

    def test_list_jobs_pagination(self, client):
        """Test job listing pagination."""
        # Test first page
        response = client.get("/api/v1/jobs?page=1&page_size=5")
        assert response.status_code == 200
        data = response.json()
        assert data["page"] == 1
        assert data["page_size"] == 5
        assert len(data["jobs"]) <= 5


@pytest.mark.integration
class TestJobCancellation:
    """Tests for job cancellation."""

    def test_cancel_pending_job(self, client, sample_pdf_path):
        """Test cancelling a pending job."""
        # Submit job
        submit_response = client.post("/api/v1/jobs", json={
            "source": "file_upload",
            "file_path": str(sample_pdf_path),
            "tenant_id": "tenant-test"
        })
        job_id = submit_response.json()["job_id"]

        # Cancel it
        cancel_response = client.delete(f"/api/v1/jobs/{job_id}")
        assert cancel_response.status_code == 204

        # Verify it's cancelled
        get_response = client.get(f"/api/v1/jobs/{job_id}")
        data = get_response.json()
        assert data["status"] == "cancelled"

    def test_cancel_nonexistent_job(self, client):
        """Test cancelling a job that doesn't exist."""
        response = client.delete("/api/v1/jobs/nonexistent-job-id")
        assert response.status_code == 404


# Run tests with:
# pytest tests/integration/test_api_endpoints.py -v
# pytest tests/integration/test_api_endpoints.py -v -m integration
