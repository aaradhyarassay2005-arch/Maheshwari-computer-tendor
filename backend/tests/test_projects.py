import os
import pytest
from uuid import uuid4
from decimal import Decimal
from datetime import date
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models import PastProject
from app.domain.repositories import IPDFExtractor
from app.infrastructure.repositories.projects import SQLAlchemyPastProjectRepository
from app.infrastructure.extractors.project_extractor import RuleBasedProjectExtractor
from app.application.project_service import ProjectService
from app.infrastructure.storage.local import LocalStorageProvider
from app.api.dependencies import get_primary_extractor, get_fallback_extractor, get_project_service
from app.main import app

# Test data texts
LOA_TEXT = """
Letter of Award (LOA)
Reference No: LOA/2026/089
Award of work for: Cisco Switch and Networking deployment for new office
Issued by: Delhi Metro Rail Corporation
Contract Value: Rs. 1,250,000.00
Date of Completion: 31/12/2026
Location: New Delhi
"""

CERTIFICATE_TEXT = """
Completion Certificate
Work Name: Supply and installation of optical fiber cable 24 Core
Employer: Central Railway
Value of Work: INR 500,000
Completed on: 10-10-2025
Place of execution: Mumbai
"""

INVOICE_TEXT = """
TAX INVOICE
Invoice No: INV-2026-99
Description of work: Excavation and concrete reinforcement work for foundation
Issued by: Delhi Development Authority
Invoiced Amount: Rs. 2,500,000.00
Invoice Date: 15/05/2026
Location: Dwarka, Delhi
"""


class MockPDFExtractor(IPDFExtractor):
    def __init__(self, text: str, should_fail: bool = False):
        self.text = text
        self.should_fail = should_fail

    async def extract_text(self, file_path: str) -> str:
        if self.should_fail:
            raise Exception("Mock extraction failed")
        return self.text


@pytest.mark.asyncio
async def test_rule_based_project_extractor():
    extractor = RuleBasedProjectExtractor()

    # 1. Test LOA text (Networking domain classification)
    loa_extracted = await extractor.extract_project_details(LOA_TEXT, "LOA")
    assert loa_extracted["project_name"] == "Cisco Switch and Networking deployment for new office"
    assert loa_extracted["client"] == "Delhi Metro Rail Corporation"
    assert loa_extracted["project_value"] == Decimal("1250000.00")
    assert loa_extracted["completion_date"] == date(2026, 12, 31)
    assert loa_extracted["location"] == "New Delhi"
    assert loa_extracted["domain"] == "Networking"

    # 2. Test Certificate text (OFC domain classification)
    cert_extracted = await extractor.extract_project_details(CERTIFICATE_TEXT, "COMPLETION_CERTIFICATE")
    assert cert_extracted["project_name"] == "Supply and installation of optical fiber cable 24 Core"
    assert cert_extracted["client"] == "Central Railway"
    assert cert_extracted["project_value"] == Decimal("500000.00")
    assert cert_extracted["completion_date"] == date(2025, 10, 10)
    assert cert_extracted["location"] == "Mumbai"
    assert cert_extracted["domain"] == "OFC"

    # 3. Test Invoice text (Civil Work domain classification)
    inv_extracted = await extractor.extract_project_details(INVOICE_TEXT, "INVOICE")
    assert inv_extracted["project_name"] == "Excavation and concrete reinforcement work for foundation"
    assert inv_extracted["client"] == "Delhi Development Authority"
    assert inv_extracted["project_value"] == Decimal("2500000.00")
    assert inv_extracted["completion_date"] == date(2026, 5, 15)
    assert inv_extracted["location"] == "Dwarka, Delhi"
    assert inv_extracted["domain"] == "Civil Work"


@pytest.mark.asyncio
async def test_project_repository_and_service(db_session: AsyncSession):
    repo = SQLAlchemyPastProjectRepository(db_session)
    extractor = RuleBasedProjectExtractor()
    storage = LocalStorageProvider(base_dir="tests/test_files/temp_storage")
    primary = MockPDFExtractor(LOA_TEXT)
    fallback = MockPDFExtractor("")

    service = ProjectService(
        project_repo=repo,
        extractor=extractor,
        storage=storage,
        primary_extractor=primary,
        fallback_extractor=fallback
    )

    # Ingest project
    project = await service.extract_and_save_project(
        filename="loa.pdf",
        content=b"%PDF-1.4 Mock PDF content",
        doc_type="LOA"
    )

    assert project.id is not None
    assert project.project_name == "Cisco Switch and Networking deployment for new office"
    assert project.client == "Delhi Metro Rail Corporation"
    assert project.project_value == Decimal("1250000.00")
    assert project.completion_date == date(2026, 12, 31)
    assert project.domain == "Networking"
    assert project.location == "New Delhi"
    assert project.document_path.endswith("loa.pdf")

    # Ingest negative value project to test validation
    neg_primary = MockPDFExtractor("""
    Name of work: Earthing work
    Client: Eastern Railway
    Value of Work: Rs. -50,000.00
    Completed on: 01/01/2026
    Location: Kolkata
    """)
    service_neg = ProjectService(
        project_repo=repo,
        extractor=extractor,
        storage=storage,
        primary_extractor=neg_primary,
        fallback_extractor=fallback
    )
    neg_project = await service_neg.extract_and_save_project(
        filename="neg.pdf",
        content=b"negative value pdf",
        doc_type="WORK_ORDER"
    )
    # Negative value is reset to Decimal("0.00")
    assert neg_project.project_value == Decimal("0.00")
    assert neg_project.domain == "Electrical Work"

    # Query list
    projects, count = await service.list_projects(skip=0, limit=10)
    assert count == 2
    assert len(projects) == 2

    # Query with filters
    projects_filtered, count_filtered = await service.list_projects(
        search="Metro",
        domain="Networking",
        min_value=Decimal("1000000.00")
    )
    assert count_filtered == 1
    assert projects_filtered[0].project_name == "Cisco Switch and Networking deployment for new office"

    # Query aggregates (capabilities)
    caps = await service.get_capabilities()
    assert len(caps) == 2  # Networking, Electrical Work

    networking_cap = next(c for c in caps if c["domain"] == "Networking")
    assert networking_cap["project_count"] == 1
    assert networking_cap["total_value"] == Decimal("1250000.00")
    assert networking_cap["max_value"] == Decimal("1250000.00")
    assert "New Delhi" in networking_cap["locations"]

    # Cleanup temp storage
    if os.path.exists("tests/test_files/temp_storage"):
        import shutil
        shutil.rmtree("tests/test_files/temp_storage")


@pytest.mark.asyncio
async def test_project_api_endpoints(client: AsyncClient):
    # Override PDF extractors
    app.dependency_overrides[get_primary_extractor] = lambda: MockPDFExtractor(CERTIFICATE_TEXT)
    app.dependency_overrides[get_fallback_extractor] = lambda: MockPDFExtractor("")

    try:
        # 1. Test POST /extract
        files = {"file": ("cert.pdf", b"pdf content", "application/pdf")}
        response = await client.post(
            "/api/v1/projects/extract",
            params={"document_type": "COMPLETION_CERTIFICATE"},
            files=files
        )
        assert response.status_code == 201
        data = response.json()
        assert data["project_name"] == "Supply and installation of optical fiber cable 24 Core"
        assert data["client"] == "Central Railway"
        assert Decimal(data["project_value"]) == Decimal("500000.00")
        assert data["domain"] == "OFC"
        assert data["location"] == "Mumbai"

        # 2. Test GET /projects
        list_response = await client.get("/api/v1/projects")
        assert list_response.status_code == 200
        list_data = list_response.json()
        assert list_data["total"] == 1
        assert list_data["items"][0]["project_name"] == "Supply and installation of optical fiber cable 24 Core"

        # Test GET /projects with search and filter
        filtered_res = await client.get(
            "/api/v1/projects",
            params={"search": "Railway", "domain": "OFC", "min_value": 100000}
        )
        assert filtered_res.status_code == 200
        assert filtered_res.json()["total"] == 1

        # 3. Test GET /projects/capabilities
        caps_response = await client.get("/api/v1/projects/capabilities")
        assert caps_response.status_code == 200
        caps_data = caps_response.json()
        assert len(caps_data) == 1
        assert caps_data[0]["domain"] == "OFC"
        assert caps_data[0]["project_count"] == 1
        assert Decimal(caps_data[0]["total_value"]) == Decimal("500000.00")
        assert "Mumbai" in caps_data[0]["locations"]

        # 4. Test upload invalid type
        invalid_type_res = await client.post(
            "/api/v1/projects/extract",
            params={"document_type": "INVALID_TYPE"},
            files=files
        )
        assert invalid_type_res.status_code == 400

    finally:
        app.dependency_overrides.clear()
        if os.path.exists("data/pdfs/cert.pdf"):
            os.remove("data/pdfs/cert.pdf")
