from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Query
from decimal import Decimal
from typing import Optional, List
import structlog

from app.api.dependencies import get_project_service
from app.application.project_service import ProjectService
from app.schemas.project import PastProjectResponse, ProjectsListResponse, CapabilityResponse

logger = structlog.get_logger("app.api.projects")
router = APIRouter(prefix="/projects", tags=["projects"])


@router.post(
    "/extract",
    response_model=PastProjectResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload project document, extract details, and store in knowledge base",
)
async def extract_and_save_project(
    document_type: str = Query(..., description="Document type: LOA, WORK_ORDER, COMPLETION_CERTIFICATE, or INVOICE"),
    file: UploadFile = File(...),
    service: ProjectService = Depends(get_project_service),
):
    valid_types = {"LOA", "WORK_ORDER", "COMPLETION_CERTIFICATE", "INVOICE"}
    doc_type_upper = document_type.upper()
    if doc_type_upper not in valid_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid document type. Must be one of: {', '.join(valid_types)}"
        )

    content = await file.read()
    if not content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty"
        )

    try:
        project = await service.extract_and_save_project(
            filename=file.filename,
            content=content,
            doc_type=doc_type_upper
        )
        return project
    except Exception as e:
        logger.error("Failed to extract project document", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process project document: {str(e)}"
        )


@router.get(
    "",
    response_model=ProjectsListResponse,
    summary="Query past projects with search and filters",
)
async def list_projects(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    search: Optional[str] = Query(None, min_length=1),
    domain: Optional[str] = None,
    location: Optional[str] = None,
    min_value: Optional[Decimal] = Query(None, ge=0),
    service: ProjectService = Depends(get_project_service),
):
    projects, total = await service.list_projects(
        skip=skip,
        limit=limit,
        search=search,
        domain=domain,
        location=location,
        min_value=min_value
    )
    return ProjectsListResponse(items=projects, total=total)


@router.get(
    "/capabilities",
    response_model=List[CapabilityResponse],
    summary="Get business capability summaries grouped by domain",
)
async def get_capabilities(
    service: ProjectService = Depends(get_project_service),
):
    return await service.get_capabilities()
