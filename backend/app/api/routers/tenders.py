from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from pydantic import UUID4

from app.api.dependencies import get_tender_service, get_audit_service
from app.application.services import TenderService
from app.application.audit_service import AuditLoggingService
from app.schemas.tenders import (
    TenderResponse,
    TendersListResponse,
    TenderCreateRequest,
    TenderUpdateRequest,
)


router = APIRouter(prefix="/tenders", tags=["tenders"])


@router.post(
    "",
    response_model=TenderResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new tender",
)
async def create_tender(
    request: TenderCreateRequest,
    http_request: Request,
    service: TenderService = Depends(get_tender_service),
    audit_service: AuditLoggingService = Depends(get_audit_service),
):
    tender = await service.create_tender(
        tender_number=request.tender_number,
        department=request.department,
        source_url=request.source_url,
        tender_value=request.tender_value,
        closing_date=request.closing_date,
    )
    
    try:
        await audit_service.log_action(
            action="TENDER_CREATION",
            resource_type="tender",
            resource_id=str(tender.id),
            ip_address=http_request.client.host if http_request.client else None,
            client_agent=http_request.headers.get("user-agent"),
            change_diff={
                "tender_number": request.tender_number,
                "department": request.department,
                "tender_value": str(request.tender_value) if request.tender_value else None,
            }
        )
    except Exception:
        pass
        
    return tender


@router.get(
    "",
    response_model=TendersListResponse,
    summary="List tenders with pagination and searching",
)
async def list_tenders(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    search: Optional[str] = Query(None),
    service: TenderService = Depends(get_tender_service),
):
    tenders, total = await service.list_tenders(skip=skip, limit=limit, search=search)
    return TendersListResponse(items=tenders, total=total)


@router.get(
    "/{id}",
    response_model=TenderResponse,
    summary="Get tender details by UUID",
)
async def get_tender(
    id: UUID4,
    service: TenderService = Depends(get_tender_service),
):
    tender = await service.get_tender(id)
    if not tender:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tender with ID {id} not found",
        )
    return tender


@router.patch(
    "/{id}",
    response_model=TenderResponse,
    summary="Partially update a tender (PATCH)",
)
async def patch_tender(
    id: UUID4,
    request: TenderUpdateRequest,
    service: TenderService = Depends(get_tender_service),
):
    return await service.update_tender(
        id=id,
        tender_number=request.tender_number,
        department=request.department,
        source_url=request.source_url,
        tender_value=request.tender_value,
        closing_date=request.closing_date,
        status=request.status,
    )


@router.delete(
    "/{id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a tender",
)
async def delete_tender(
    id: UUID4,
    request: Request,
    service: TenderService = Depends(get_tender_service),
    audit_service: AuditLoggingService = Depends(get_audit_service),
):
    deleted = await service.delete_tender(id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tender with ID {id} not found",
        )
        
    try:
        await audit_service.log_action(
            action="TENDER_DELETION",
            resource_type="tender",
            resource_id=str(id),
            ip_address=request.client.host if request.client else None,
            client_agent=request.headers.get("user-agent"),
        )
    except Exception:
        pass
        
    return None
