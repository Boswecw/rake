"""Test database telemetry client with sample data."""

import asyncio
import sys
from pathlib import Path
from uuid import uuid4
from datetime import datetime, timedelta

# Add rake to path
sys.path.insert(0, str(Path(__file__).parent))

from services.telemetry_db_client import TelemetryDatabaseClient


async def test_telemetry():
    """Generate sample Rake telemetry events."""

    print("🔧 Testing Rake Database Telemetry Client\n")

    # Initialize client
    db_path = "/home/charles/projects/Coding2025/Forge/DataForge/dataforge.db"
    client = TelemetryDatabaseClient(db_path=db_path, enabled=True)

    print(f"✅ Connected to database: {db_path}\n")

    # Generate 5 pipeline runs with realistic data
    pipelines = [
        {"id": "pdf-processor", "name": "PDF Document Pipeline", "success_rate": 0.95},
        {"id": "web-scraper", "name": "Web Scraping Pipeline", "success_rate": 0.90},
        {"id": "sec-edgar", "name": "SEC EDGAR Filings", "success_rate": 0.98},
        {"id": "api-ingestion", "name": "API Data Ingestion", "success_rate": 0.85},
        {"id": "db-sync", "name": "Database Synchronization", "success_rate": 0.92},
    ]

    print("📊 Generating sample pipeline events...\n")

    for i, pipeline in enumerate(pipelines):
        correlation_id = str(uuid4())
        job_id = f"job-{pipeline['id']}-{i+1}"

        # Simulate events over the last 24 hours
        hours_ago = 24 - (i * 5)  # Spread events over time
        timestamp = (datetime.utcnow() - timedelta(hours=hours_ago)).isoformat()

        print(f"  Pipeline: {pipeline['name']}")
        print(f"    Job ID: {job_id}")
        print(f"    Time: {hours_ago} hours ago")

        # Job started
        await client.emit_job_started(
            job_id=job_id,
            source="file_upload",
            correlation_id=correlation_id,
            scheduled=True,
            tenant_id="default",
            metadata={
                "pipeline_id": pipeline['id'],
                "pipeline_name": pipeline['name']
            }
        )

        # Phase completed events (simulate 5 pipeline stages)
        phases = [
            ("fetch", 1, 500),
            ("clean", 2, 300),
            ("chunk", 3, 800),
            ("embed", 4, 1500),
            ("store", 5, 400)
        ]

        for phase_name, phase_num, duration in phases:
            await client.emit_phase_completed(
                job_id=job_id,
                phase=phase_name,
                phase_number=phase_num,
                correlation_id=correlation_id,
                duration_ms=duration,
                items_processed=10 + (i * 5),
                tenant_id="default",
                metadata={
                    "pipeline_id": pipeline['id'],
                    "pipeline_name": pipeline['name']
                }
            )

        # Job completed (or failed based on success rate)
        import random
        if random.random() < pipeline['success_rate']:
            await client.emit_job_completed(
                job_id=job_id,
                source="file_upload",
                correlation_id=correlation_id,
                total_duration_ms=3500 + (i * 200),
                chunks_created=50 + (i * 10),
                embeddings_generated=50 + (i * 10),
                tenant_id="default",
                metadata={
                    "pipeline_id": pipeline['id'],
                    "pipeline_name": pipeline['name']
                }
            )
            print(f"    Status: ✅ Completed\n")
        else:
            await client.emit_job_failed(
                job_id=job_id,
                source="file_upload",
                correlation_id=correlation_id,
                failed_stage="embed",
                error_type="RateLimitError",
                error_message="OpenAI rate limit exceeded",
                retry_count=2,
                tenant_id="default",
                metadata={
                    "pipeline_id": pipeline['id'],
                    "pipeline_name": pipeline['name']
                }
            )
            print(f"    Status: ❌ Failed\n")

    # Generate additional recent events for activity
    print("📈 Generating recent activity (last hour)...\n")

    for i in range(10):
        correlation_id = str(uuid4())
        job_id = f"job-recent-{i+1}"
        pipeline = pipelines[i % len(pipelines)]

        await client.emit_job_completed(
            job_id=job_id,
            source="scheduled",
            correlation_id=correlation_id,
            total_duration_ms=2000 + (i * 100),
            chunks_created=30,
            embeddings_generated=30,
            tenant_id="default",
            metadata={
                "pipeline_id": pipeline['id'],
                "pipeline_name": pipeline['name']
            }
        )

    print("  ✅ Generated 10 recent ingestion events\n")

    await client.close()

    print("✅ Test completed successfully!")
    print("\n🎯 Next steps:")
    print("  1. Open ForgeCommand at http://localhost:1420/")
    print("  2. Navigate to the Rake dashboard")
    print("  3. Verify telemetry data is displayed")


if __name__ == "__main__":
    asyncio.run(test_telemetry())
