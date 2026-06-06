import pytest
from httpx import AsyncClient
from app.core.config import settings

@pytest.mark.asyncio
async def test_metrics_endpoint_public(client: AsyncClient):
    # Ensure no credentials are set
    settings.METRICS_USERNAME = None
    settings.METRICS_PASSWORD = None
    
    response = await client.get("/api/v1/metrics")
    assert response.status_code == 200
    assert "text/plain" in response.headers.get("content-type", "")
    content = response.text
    # Check that custom metrics exist in metrics dump
    assert "tender_processing_duration_seconds" in content
    assert "tender_download_failures_total" in content
    assert "recommendation_latency_seconds" in content
    assert "qdrant_search_duration_seconds" in content
    assert "gemini_response_duration_seconds" in content

@pytest.mark.asyncio
async def test_metrics_endpoint_basic_auth(client: AsyncClient):
    # Set credentials
    settings.METRICS_USERNAME = "admin"
    settings.METRICS_PASSWORD = "password123"
    
    try:
        # Request without credentials -> should fail
        response = await client.get("/api/v1/metrics")
        assert response.status_code == 401
        assert "WWW-Authenticate" in response.headers
        
        # Request with incorrect credentials -> should fail
        response = await client.get("/api/v1/metrics", auth=("admin", "wrong"))
        assert response.status_code == 401
        
        # Request with correct credentials -> should succeed
        response = await client.get("/api/v1/metrics", auth=("admin", "password123"))
        assert response.status_code == 200
    finally:
        # Reset config
        settings.METRICS_USERNAME = None
        settings.METRICS_PASSWORD = None

@pytest.mark.asyncio
async def test_client_telemetry_logs_endpoint(client: AsyncClient):
    payload = {
        "level": "error",
        "message": "Frontend connection timed out",
        "trace_id": "0123456789abcdef0123456789abcdef",
        "url": "http://localhost:3000/tenders",
        "stack_trace": "Error: Timeout\n    at fetch..."
    }
    
    response = await client.post("/api/v1/telemetry/logs", json=payload)
    assert response.status_code == 202
    assert response.json() == {"status": "accepted"}
