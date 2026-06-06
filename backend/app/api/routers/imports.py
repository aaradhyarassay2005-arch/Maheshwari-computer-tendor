from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, status, Request
from app.api.dependencies import get_tender_service, get_audit_service
from app.application.services import TenderService
from app.application.audit_service import AuditLoggingService
from app.schemas.imports import ExcelImportResponse

router = APIRouter(prefix="/imports", tags=["imports"])


@router.post(
    "/excel",
    response_model=ExcelImportResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload Excel sheet to batch import tenders",
)
async def import_excel(
    request: Request,
    file: UploadFile = File(...),
    service: TenderService = Depends(get_tender_service),
    audit_service: AuditLoggingService = Depends(get_audit_service),
):
    filename = file.filename or ""
    if not (filename.endswith(".xlsx") or filename.endswith(".xls")):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file format. Only Excel files (.xlsx, .xls) are supported.",
        )

    try:
        content = await file.read()
        summary = await service.import_tenders_from_excel(content)
        
        # Log Audit Trail
        try:
            await audit_service.log_action(
                action="EXCEL_IMPORT",
                resource_type="import",
                resource_id=filename,
                ip_address=request.client.host if request.client else None,
                client_agent=request.headers.get("user-agent"),
                change_diff={
                    "filename": filename,
                    "imported_count": summary.imported_count,
                    "failed_count": summary.failed_count,
                }
            )
        except Exception:
            pass
            
        return summary
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
