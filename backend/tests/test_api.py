import pytest
from httpx import AsyncClient
from uuid import uuid4


@pytest.mark.asyncio
async def test_health_check(client: AsyncClient):
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


@pytest.mark.asyncio
async def test_create_tender_api(client: AsyncClient):
    payload = {
        "tender_number": "T-API-001",
        "department": "Civil Engineering",
        "source_url": "https://example.com/sleepers.pdf",
        "tender_value": 750000.00,
        "closing_date": "2026-12-15"
    }
    response = await client.post("/api/v1/tenders", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["id"] is not None
    assert data["tender_number"] == "T-API-001"
    assert data["department"] == "Civil Engineering"
    assert float(data["tender_value"]) == 750000.00
    assert data["closing_date"] == "2026-12-15"
    assert data["status"] == "NEW"


@pytest.mark.asyncio
async def test_create_tender_api_duplicate(client: AsyncClient):
    payload = {
        "tender_number": "T-API-002",
        "department": "Mechanical",
        "source_url": "https://example.com/sleepers.pdf"
    }
    res1 = await client.post("/api/v1/tenders", json=payload)
    assert res1.status_code == 201

    res2 = await client.post("/api/v1/tenders", json=payload)
    assert res2.status_code == 409
    assert "already exists" in res2.json()["detail"]


@pytest.mark.asyncio
async def test_create_tender_api_invalid_value(client: AsyncClient):
    payload = {
        "tender_number": "T-API-NEG",
        "department": "Mechanical",
        "source_url": "https://example.com/sleepers.pdf",
        "tender_value": -100.50
    }
    response = await client.post("/api/v1/tenders", json=payload)
    assert response.status_code == 422  # Pydantic validation error


@pytest.mark.asyncio
async def test_get_tender_api_not_found(client: AsyncClient):
    random_id = str(uuid4())
    response = await client.get(f"/api/v1/tenders/{random_id}")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_list_tenders_api(client: AsyncClient):
    await client.post(
        "/api/v1/tenders", 
        json={"tender_number": "T-LIST-1", "department": "Civil", "source_url": "http://x"}
    )
    await client.post(
        "/api/v1/tenders", 
        json={"tender_number": "T-LIST-2", "department": "Electrical", "source_url": "http://x"}
    )

    response = await client.get("/api/v1/tenders")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    assert len(data["items"]) == 2


@pytest.mark.asyncio
async def test_patch_tender_api(client: AsyncClient):
    res_tender = await client.post(
        "/api/v1/tenders", 
        json={"tender_number": "T-PATCH-1", "department": "Before Patch", "source_url": "http://x"}
    )
    tender_id = res_tender.json()["id"]

    patch_payload = {
        "department": "After Patch",
        "tender_value": 999.99,
        "status": "DOWNLOADED"
    }
    res_patch = await client.patch(f"/api/v1/tenders/{tender_id}", json=patch_payload)
    assert res_patch.status_code == 200
    patched_data = res_patch.json()
    assert patched_data["department"] == "After Patch"
    assert float(patched_data["tender_value"]) == 999.99
    assert patched_data["status"] == "DOWNLOADED"


@pytest.mark.asyncio
async def test_delete_tender_api(client: AsyncClient):
    res_tender = await client.post(
        "/api/v1/tenders", 
        json={"tender_number": "T-DEL-1", "department": "Delete", "source_url": "http://x"}
    )
    tender_id = res_tender.json()["id"]

    res_del = await client.delete(f"/api/v1/tenders/{tender_id}")
    assert res_del.status_code == 204

    res_get = await client.get(f"/api/v1/tenders/{tender_id}")
    assert res_get.status_code == 404
