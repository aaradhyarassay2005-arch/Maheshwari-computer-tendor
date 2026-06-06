import structlog
from datetime import datetime, timezone
from uuid import uuid4
from pydantic import UUID4
from decimal import Decimal
from typing import Optional

from app.domain.models import TenderMetadata, TenderDocumentStatus, TenderStatus
from app.domain.repositories import (
    ITenderRepository,
    ITenderDocumentRepository,
    ITenderMetadataRepository,
    IPDFExtractor,
    IMetadataExtractionProvider,
)

logger = structlog.get_logger("app.extraction")


class TenderMetadataExtractionService:
    def __init__(
        self,
        tender_repo: ITenderRepository,
        doc_repo: ITenderDocumentRepository,
        metadata_repo: ITenderMetadataRepository,
        primary_extractor: IPDFExtractor,
        fallback_extractor: IPDFExtractor,
        extraction_provider: IMetadataExtractionProvider,
    ):
        self.tender_repo = tender_repo
        self.doc_repo = doc_repo
        self.metadata_repo = metadata_repo
        self.primary_extractor = primary_extractor
        self.fallback_extractor = fallback_extractor
        self.extraction_provider = extraction_provider

    async def extract_metadata(self, tender_id: UUID4) -> Optional[TenderMetadata]:
        import time
        from app.core.observability import TENDER_PROCESSING_TIME, EXTRACTION_ACCURACY
        
        start_time = time.time()
        status = "FAILED"
        try:
            doc = await self.doc_repo.get_by_tender_id(tender_id)
            if not doc or doc.status != TenderDocumentStatus.DOWNLOADED:
                logger.error("No downloaded document found for extraction", tender_id=str(tender_id))
                return None

            tender = await self.tender_repo.get_by_id(tender_id)
            if not tender:
                logger.error("Tender not found for extraction", tender_id=str(tender_id))
                return None

            raw_text = ""
            # 1. Primary Extractor (pdfplumber)
            try:
                logger.info("Attempting primary text extraction (pdfplumber)", tender_id=str(tender_id), path=doc.file_path)
                raw_text = await self.primary_extractor.extract_text(doc.file_path)
            except Exception as e:
                logger.warn("Primary extractor failed, falling back", error=str(e), tender_id=str(tender_id))

            # 2. Fallback Extractor (PyMuPDF / fitz)
            if not raw_text or not raw_text.strip():
                try:
                    logger.info("Attempting fallback text extraction (PyMuPDF)", tender_id=str(tender_id), path=doc.file_path)
                    raw_text = await self.fallback_extractor.extract_text(doc.file_path)
                except Exception as e:
                    logger.error("Fallback extractor failed", error=str(e), tender_id=str(tender_id))

            if not raw_text or not raw_text.strip():
                logger.error("All text extraction strategies failed", tender_id=str(tender_id))
                tender.status = TenderStatus.FAILED
                tender.updated_at = datetime.now(timezone.utc)
                await self.tender_repo.update(tender)
                return None

            # 3. Parse Metadata
            try:
                logger.info("Parsing metadata fields from raw text", tender_id=str(tender_id))
                extracted_data = await self.extraction_provider.extract(raw_text)

                # 4. Enforce validations / cleanup
                # Value cannot be negative
                tender_value = extracted_data.get("tender_value")
                if tender_value is not None and tender_value < Decimal("0.0"):
                    logger.warn("Extracted negative tender_value, resetting to None", tender_id=str(tender_id), value=str(tender_value))
                    extracted_data["tender_value"] = None
                    extracted_data["tender_value_confidence"] = 0.0

                emd = extracted_data.get("emd")
                if emd is not None and emd < Decimal("0.0"):
                    logger.warn("Extracted negative EMD, resetting to None", tender_id=str(tender_id), value=str(emd))
                    extracted_data["emd"] = None
                    extracted_data["emd_confidence"] = 0.0

                # 5. Create or Update TenderMetadata Entity
                now = datetime.now(timezone.utc)
                existing_meta = await self.metadata_repo.get_by_tender_id(tender_id)

                if existing_meta:
                    metadata = TenderMetadata(
                        id=existing_meta.id,
                        tender_id=tender_id,
                        document_id=doc.id,
                        tender_number=extracted_data["tender_number"],
                        tender_number_confidence=extracted_data["tender_number_confidence"],
                        department=extracted_data["department"],
                        department_confidence=extracted_data["department_confidence"],
                        tender_value=extracted_data["tender_value"],
                        tender_value_confidence=extracted_data["tender_value_confidence"],
                        emd=extracted_data["emd"],
                        emd_confidence=extracted_data["emd_confidence"],
                        closing_date=extracted_data["closing_date"],
                        closing_date_confidence=extracted_data["closing_date_confidence"],
                        completion_period=extracted_data["completion_period"],
                        completion_period_confidence=extracted_data["completion_period_confidence"],
                        tender_type=extracted_data["tender_type"],
                        tender_type_confidence=extracted_data["tender_type_confidence"],
                        zone=extracted_data["zone"],
                        zone_confidence=extracted_data["zone_confidence"],
                        bid_system=extracted_data["bid_system"],
                        bid_system_confidence=extracted_data["bid_system_confidence"],
                        contract_type=extracted_data["contract_type"],
                        contract_type_confidence=extracted_data["contract_type_confidence"],
                        raw_text=raw_text,
                        created_at=existing_meta.created_at,
                        updated_at=now,
                    )
                    saved_meta = await self.metadata_repo.update(metadata)
                else:
                    metadata = TenderMetadata(
                        id=uuid4(),
                        tender_id=tender_id,
                        document_id=doc.id,
                        tender_number=extracted_data["tender_number"],
                        tender_number_confidence=extracted_data["tender_number_confidence"],
                        department=extracted_data["department"],
                        department_confidence=extracted_data["department_confidence"],
                        tender_value=extracted_data["tender_value"],
                        tender_value_confidence=extracted_data["tender_value_confidence"],
                        emd=extracted_data["emd"],
                        emd_confidence=extracted_data["emd_confidence"],
                        closing_date=extracted_data["closing_date"],
                        closing_date_confidence=extracted_data["closing_date_confidence"],
                        completion_period=extracted_data["completion_period"],
                        completion_period_confidence=extracted_data["completion_period_confidence"],
                        tender_type=extracted_data["tender_type"],
                        tender_type_confidence=extracted_data["tender_type_confidence"],
                        zone=extracted_data["zone"],
                        zone_confidence=extracted_data["zone_confidence"],
                        bid_system=extracted_data["bid_system"],
                        bid_system_confidence=extracted_data["bid_system_confidence"],
                        contract_type=extracted_data["contract_type"],
                        contract_type_confidence=extracted_data["contract_type_confidence"],
                        raw_text=raw_text,
                        created_at=now,
                        updated_at=now,
                    )
                    saved_meta = await self.metadata_repo.add(metadata)

                # 6. Automatically update parent Tender fields & status
                if extracted_data["tender_value"] is not None:
                    tender.tender_value = extracted_data["tender_value"]
                if extracted_data["closing_date"] is not None:
                    tender.closing_date = extracted_data["closing_date"]
                
                # Transition status to PARSED
                tender.status = TenderStatus.PARSED
                tender.updated_at = now
                await self.tender_repo.update(tender)

                status = "SUCCESS"
                
                # Record accuracy metrics
                try:
                    t_str = str(tender_id)
                    EXTRACTION_ACCURACY.labels(field_name="tender_number", tender_id=t_str).set(metadata.tender_number_confidence)
                    EXTRACTION_ACCURACY.labels(field_name="department", tender_id=t_str).set(metadata.department_confidence)
                    EXTRACTION_ACCURACY.labels(field_name="tender_value", tender_id=t_str).set(metadata.tender_value_confidence)
                    EXTRACTION_ACCURACY.labels(field_name="emd", tender_id=t_str).set(metadata.emd_confidence)
                except Exception:
                    pass

                logger.info("Tender metadata extraction completed successfully", tender_id=str(tender_id), meta_id=str(saved_meta.id))
                return saved_meta

            except Exception as e:
                logger.error("Metadata parsing or mapping encountered an error", error=str(e), tender_id=str(tender_id))
                tender.status = TenderStatus.FAILED
                tender.updated_at = datetime.now(timezone.utc)
                await self.tender_repo.update(tender)
                return None
        finally:
            duration = time.time() - start_time
            try:
                TENDER_PROCESSING_TIME.labels(status=status).observe(duration)
            except Exception:
                pass
