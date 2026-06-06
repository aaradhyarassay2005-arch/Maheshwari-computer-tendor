import json
from datetime import datetime, timezone
from uuid import uuid4
from pydantic import UUID4
import structlog

from app.domain.models import TenderStatus, TenderReview, Tender
from app.domain.repositories import ITenderRepository, ITenderMetadataRepository, ITenderReviewRepository
from app.schemas.reviews import ReviewSubmitRequest, ReviewResponse
from app.application.audit_service import AuditLoggingService

logger = structlog.get_logger("app.application.review")


class TenderReviewService:
    def __init__(
        self,
        tender_repository: ITenderRepository,
        metadata_repository: ITenderMetadataRepository,
        review_repository: ITenderReviewRepository,
        audit_service: AuditLoggingService
    ):
        self.tender_repository = tender_repository
        self.metadata_repository = metadata_repository
        self.review_repository = review_repository
        self.audit_service = audit_service

    async def get_review_queue(self) -> list[Tender]:
        # Returns all tenders in PARSED status
        return await self.tender_repository.get_by_statuses([TenderStatus.PARSED])

    async def get_review_history(self, tender_id: UUID4) -> list[ReviewResponse]:
        reviews = await self.review_repository.get_by_tender_id(tender_id)
        results = []
        for r in reviews:
            try:
                orig = json.loads(r.original_values)
            except Exception:
                orig = {}
            try:
                corr = json.loads(r.corrected_values)
            except Exception:
                corr = {}
            results.append(
                ReviewResponse(
                    id=r.id,
                    tender_id=r.tender_id,
                    verdict=r.verdict,
                    reviewer_id=r.reviewer_id,
                    reviewed_at=r.reviewed_at,
                    original_values=orig,
                    corrected_values=corr,
                    comments=r.comments
                )
            )
        return results

    async def submit_review(self, tender_id: UUID4, request: ReviewSubmitRequest) -> ReviewResponse:
        tender = await self.tender_repository.get_by_id(tender_id)
        if not tender:
            raise ValueError(f"Tender with ID {tender_id} not found")

        if tender.status not in (TenderStatus.PARSED, TenderStatus.APPROVED, TenderStatus.REJECTED):
            raise ValueError(f"Tender is in status {tender.status} and cannot be reviewed")

        metadata = await self.metadata_repository.get_by_tender_id(tender_id)
        
        # Snapshot original metadata values
        original_dict = {}
        if metadata:
            original_dict = {
                "tender_number": metadata.tender_number,
                "department": metadata.department,
                "tender_value": str(metadata.tender_value) if metadata.tender_value is not None else None,
                "closing_date": metadata.closing_date.isoformat() if metadata.closing_date else None,
                "emd": str(metadata.emd) if metadata.emd is not None else None,
                "completion_period": metadata.completion_period,
                "tender_type": metadata.tender_type,
                "zone": metadata.zone,
                "bid_system": metadata.bid_system,
                "contract_type": metadata.contract_type
            }

        corrected_dict = {}
        if request.corrections and metadata:
            corr = request.corrections
            
            # Apply corrections to metadata and tender ORM fields
            if corr.tender_number is not None:
                metadata.tender_number = corr.tender_number
                metadata.tender_number_confidence = 1.0
                tender.tender_number = corr.tender_number
                corrected_dict["tender_number"] = corr.tender_number
                
            if corr.department is not None:
                metadata.department = corr.department
                metadata.department_confidence = 1.0
                tender.department = corr.department
                corrected_dict["department"] = corr.department
                
            if corr.tender_value is not None:
                metadata.tender_value = corr.tender_value
                metadata.tender_value_confidence = 1.0
                tender.tender_value = corr.tender_value
                corrected_dict["tender_value"] = str(corr.tender_value)
                
            if corr.closing_date is not None:
                metadata.closing_date = corr.closing_date
                metadata.closing_date_confidence = 1.0
                tender.closing_date = corr.closing_date
                corrected_dict["closing_date"] = corr.closing_date.isoformat()
                
            if corr.emd is not None:
                metadata.emd = corr.emd
                metadata.emd_confidence = 1.0
                corrected_dict["emd"] = str(corr.emd)
                
            if corr.completion_period is not None:
                metadata.completion_period = corr.completion_period
                metadata.completion_period_confidence = 1.0
                corrected_dict["completion_period"] = corr.completion_period
                
            if corr.tender_type is not None:
                metadata.tender_type = corr.tender_type
                metadata.tender_type_confidence = 1.0
                corrected_dict["tender_type"] = corr.tender_type
                
            if corr.zone is not None:
                metadata.zone = corr.zone
                metadata.zone_confidence = 1.0
                corrected_dict["zone"] = corr.zone
                
            if corr.bid_system is not None:
                metadata.bid_system = corr.bid_system
                metadata.bid_system_confidence = 1.0
                corrected_dict["bid_system"] = corr.bid_system
                
            if corr.contract_type is not None:
                metadata.contract_type = corr.contract_type
                metadata.contract_type_confidence = 1.0
                corrected_dict["contract_type"] = corr.contract_type

        # Update status
        tender.status = request.verdict
        tender.updated_at = datetime.now(timezone.utc)

        # Persist updates
        await self.tender_repository.update(tender)
        if metadata:
            await self.metadata_repository.update(metadata)

        # Create review record
        review = TenderReview(
            id=uuid4(),
            tender_id=tender_id,
            verdict=request.verdict,
            reviewer_id=request.reviewer_id,
            reviewed_at=datetime.now(timezone.utc),
            original_values=json.dumps(original_dict),
            corrected_values=json.dumps(corrected_dict),
            comments=request.comments
        )
        await self.review_repository.add(review)

        # Log audit log
        change_diff = {
            "verdict": request.verdict,
            "original_values": original_dict,
            "corrected_values": corrected_dict,
            "comments": request.comments
        }
        await self.audit_service.log_action(
            action="SUBMIT_REVIEW",
            resource_type="tender",
            resource_id=str(tender_id),
            user_id=request.reviewer_id,
            change_diff=change_diff
        )

        logger.info(
            "Tender review submitted successfully",
            tender_id=str(tender_id),
            verdict=request.verdict,
            reviewer_id=request.reviewer_id
        )

        return ReviewResponse(
            id=review.id,
            tender_id=review.tender_id,
            verdict=review.verdict,
            reviewer_id=review.reviewer_id,
            reviewed_at=review.reviewed_at,
            original_values=original_dict,
            corrected_values=corrected_dict,
            comments=review.comments
        )
