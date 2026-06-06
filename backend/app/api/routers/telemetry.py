from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Response, Request
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from pydantic import BaseModel
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
import structlog

from app.core.config import settings

logger = structlog.get_logger("app.api.telemetry")
router = APIRouter(tags=["telemetry"])

security = HTTPBasic(auto_error=False)


class ClientLogPayload(BaseModel):
    level: str
    message: str
    trace_id: Optional[str] = None
    url: Optional[str] = None
    stack_trace: Optional[str] = None


def verify_metrics_auth(credentials: Optional[HTTPBasicCredentials] = Depends(security)):
    # Check if credentials are required in configuration settings
    if settings.METRICS_USERNAME and settings.METRICS_PASSWORD:
        if not credentials or credentials.username != settings.METRICS_USERNAME or credentials.password != settings.METRICS_PASSWORD:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid metrics credentials",
                headers={"WWW-Authenticate": "Basic"},
            )
    return True


@router.get("/metrics", summary="Prometheus metrics scraping endpoint")
async def get_metrics(auth_verified: bool = Depends(verify_metrics_auth)):
    """Returns the latest Prometheus exposition metrics data."""
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


@router.post("/telemetry/logs", status_code=status.HTTP_202_ACCEPTED, summary="Ingest client-side frontend logs")
async def ingest_client_logs(payload: ClientLogPayload, request: Request):
    """Ingests client-side exception metrics and formats them in structural logs."""
    client_ip = request.client.host if request.client else "unknown"
    
    log_data = {
        "client_ip": client_ip,
        "client_url": payload.url,
        "client_trace_id": payload.trace_id,
        "stack_trace": payload.stack_trace,
    }

    level = payload.level.upper()
    if level == "ERROR":
        logger.error(payload.message, **log_data)
    elif level == "WARN" or level == "WARNING":
        logger.warn(payload.message, **log_data)
    else:
        logger.info(payload.message, **log_data)
        
    return {"status": "accepted"}
