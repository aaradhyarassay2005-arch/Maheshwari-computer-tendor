from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db_session
from app.core.security import verify_access_token
from app.domain.models import UserRole
from app.infrastructure.db.models import UserORM
from app.infrastructure.repositories.tenders import SQLAlchemyTenderRepository
from app.infrastructure.repositories.documents import SQLAlchemyTenderDocumentRepository
from app.infrastructure.repositories.metadata import SQLAlchemyTenderMetadataRepository
from app.infrastructure.storage.local import LocalStorageProvider
from app.infrastructure.downloader.httpx import HTTPXPDFDownloader
from app.infrastructure.extractors.pdf_plumber import PDFPlumberExtractor
from app.infrastructure.extractors.pymupdf import PyMuPDFExtractor
from app.infrastructure.extractors.rule_based import RuleBasedMetadataExtractor
from app.application.services import TenderService
from app.application.downloader import TenderDownloaderService
from app.application.extraction_service import TenderMetadataExtractionService
from app.infrastructure.repositories.boq import SQLAlchemyBOQItemRepository
from app.infrastructure.extractors.camelot_boq import CamelotBOQExtractor
from app.infrastructure.extractors.pdfplumber_boq import PdfPlumberBOQExtractor
from app.application.boq_service import TenderBOQExtractionService
from app.application.boq_analytics_engine import BOQAnalyticsEngine
from app.application.boq_analytics_service import BOQAnalyticsService
from app.infrastructure.repositories.projects import SQLAlchemyPastProjectRepository
from app.infrastructure.extractors.project_extractor import RuleBasedProjectExtractor
from app.application.project_service import ProjectService
from app.infrastructure.embeddings.sentence_transformer import SentenceTransformersEmbeddingProvider
from app.infrastructure.vector_search.qdrant import QdrantVectorSearchProvider
from app.application.ranking_engine import MatchingRankingEngine
from app.application.matching_service import ProjectMatchingService
from app.application.qualification_engine import FinancialRuleEngine
from app.application.qualification_service import FinancialValidationService
from app.application.risk_engine import RiskEngine
from app.application.risk_service import RiskService
from app.application.recommendation_rules import RecommendationRulesEngine
from app.application.recommendation_service import TenderRecommendationService
from app.infrastructure.llm.gemini import GeminiLLMProvider
from app.application.analyst_service import AITenderAnalystService
from app.infrastructure.repositories.audit import SQLAlchemyAuditLogRepository
from app.application.audit_service import AuditLoggingService
from app.infrastructure.repositories.reviews import SQLAlchemyTenderReviewRepository
from app.application.review_service import TenderReviewService






async def get_tender_repository(
    session: AsyncSession = Depends(get_db_session)
) -> SQLAlchemyTenderRepository:
    return SQLAlchemyTenderRepository(session)


async def get_document_repository(
    session: AsyncSession = Depends(get_db_session)
) -> SQLAlchemyTenderDocumentRepository:
    return SQLAlchemyTenderDocumentRepository(session)


async def get_metadata_repository(
    session: AsyncSession = Depends(get_db_session)
) -> SQLAlchemyTenderMetadataRepository:
    return SQLAlchemyTenderMetadataRepository(session)


async def get_tender_service(
    repo: SQLAlchemyTenderRepository = Depends(get_tender_repository),
    doc_repo: SQLAlchemyTenderDocumentRepository = Depends(get_document_repository),
    metadata_repo: SQLAlchemyTenderMetadataRepository = Depends(get_metadata_repository),
) -> TenderService:
    """Instantiates and returns the TenderService configured with the repositories."""
    return TenderService(repo, doc_repo, metadata_repo)

def get_storage_provider() -> LocalStorageProvider:
    return LocalStorageProvider()


def get_pdf_downloader() -> HTTPXPDFDownloader:
    return HTTPXPDFDownloader()


def get_primary_extractor() -> PDFPlumberExtractor:
    return PDFPlumberExtractor()


def get_fallback_extractor() -> PyMuPDFExtractor:
    return PyMuPDFExtractor()


def get_extraction_provider() -> RuleBasedMetadataExtractor:
    return RuleBasedMetadataExtractor()


async def get_downloader_service(
    tender_repo: SQLAlchemyTenderRepository = Depends(get_tender_repository),
    doc_repo: SQLAlchemyTenderDocumentRepository = Depends(get_document_repository),
    downloader: HTTPXPDFDownloader = Depends(get_pdf_downloader),
    storage: LocalStorageProvider = Depends(get_storage_provider),
) -> TenderDownloaderService:
    return TenderDownloaderService(
        tender_repo=tender_repo,
        doc_repo=doc_repo,
        downloader=downloader,
        storage=storage,
    )


async def get_metadata_extraction_service(
    tender_repo: SQLAlchemyTenderRepository = Depends(get_tender_repository),
    doc_repo: SQLAlchemyTenderDocumentRepository = Depends(get_document_repository),
    metadata_repo: SQLAlchemyTenderMetadataRepository = Depends(get_metadata_repository),
    primary_extractor: PDFPlumberExtractor = Depends(get_primary_extractor),
    fallback_extractor: PyMuPDFExtractor = Depends(get_fallback_extractor),
    extraction_provider: RuleBasedMetadataExtractor = Depends(get_extraction_provider),
) -> TenderMetadataExtractionService:
    return TenderMetadataExtractionService(
        tender_repo=tender_repo,
        doc_repo=doc_repo,
        metadata_repo=metadata_repo,
        primary_extractor=primary_extractor,
        fallback_extractor=fallback_extractor,
        extraction_provider=extraction_provider,
    )


async def get_boq_repository(
    session: AsyncSession = Depends(get_db_session)
) -> SQLAlchemyBOQItemRepository:
    return SQLAlchemyBOQItemRepository(session)


def get_primary_boq_extractor() -> CamelotBOQExtractor:
    return CamelotBOQExtractor()


def get_fallback_boq_extractor() -> PdfPlumberBOQExtractor:
    return PdfPlumberBOQExtractor()


async def get_boq_extraction_service(
    tender_repo: SQLAlchemyTenderRepository = Depends(get_tender_repository),
    doc_repo: SQLAlchemyTenderDocumentRepository = Depends(get_document_repository),
    boq_repo: SQLAlchemyBOQItemRepository = Depends(get_boq_repository),
    primary_extractor: CamelotBOQExtractor = Depends(get_primary_boq_extractor),
    fallback_extractor: PdfPlumberBOQExtractor = Depends(get_fallback_boq_extractor),
) -> TenderBOQExtractionService:
    return TenderBOQExtractionService(
        tender_repo=tender_repo,
        doc_repo=doc_repo,
        boq_repo=boq_repo,
        primary_extractor=primary_extractor,
        fallback_extractor=fallback_extractor,
    )


def get_boq_analytics_engine() -> BOQAnalyticsEngine:
    return BOQAnalyticsEngine()


async def get_boq_analytics_service(
    tender_repo: SQLAlchemyTenderRepository = Depends(get_tender_repository),
    boq_repo: SQLAlchemyBOQItemRepository = Depends(get_boq_repository),
    analytics_engine: BOQAnalyticsEngine = Depends(get_boq_analytics_engine),
) -> BOQAnalyticsService:
    return BOQAnalyticsService(
        tender_repo=tender_repo,
        boq_repo=boq_repo,
        analytics_engine=analytics_engine,
    )


async def get_project_repository(
    session: AsyncSession = Depends(get_db_session)
) -> SQLAlchemyPastProjectRepository:
    return SQLAlchemyPastProjectRepository(session)


def get_project_extractor() -> RuleBasedProjectExtractor:
    return RuleBasedProjectExtractor()


def get_embedding_provider() -> SentenceTransformersEmbeddingProvider:
    global _embedding_provider_instance
    if "_embedding_provider_instance" not in globals():
        _embedding_provider_instance = SentenceTransformersEmbeddingProvider()
    return _embedding_provider_instance


def get_vector_search_provider() -> QdrantVectorSearchProvider:
    global _vector_search_provider_instance
    if "_vector_search_provider_instance" not in globals():
        _vector_search_provider_instance = QdrantVectorSearchProvider()
    return _vector_search_provider_instance


async def get_project_service(
    project_repo: SQLAlchemyPastProjectRepository = Depends(get_project_repository),
    extractor: RuleBasedProjectExtractor = Depends(get_project_extractor),
    storage: LocalStorageProvider = Depends(get_storage_provider),
    primary_extractor: PDFPlumberExtractor = Depends(get_primary_extractor),
    fallback_extractor: PyMuPDFExtractor = Depends(get_fallback_extractor),
    embedding_provider: SentenceTransformersEmbeddingProvider = Depends(get_embedding_provider),
    vector_search_provider: QdrantVectorSearchProvider = Depends(get_vector_search_provider),
) -> ProjectService:
    return ProjectService(
        project_repo=project_repo,
        extractor=extractor,
        storage=storage,
        primary_extractor=primary_extractor,
        fallback_extractor=fallback_extractor,
        embedding_provider=embedding_provider,
        vector_search_provider=vector_search_provider,
    )



def get_matching_ranking_engine() -> MatchingRankingEngine:
    return MatchingRankingEngine()


async def get_project_matching_service(
    project_repo: SQLAlchemyPastProjectRepository = Depends(get_project_repository),
    embedding_provider: SentenceTransformersEmbeddingProvider = Depends(get_embedding_provider),
    vector_search_provider: QdrantVectorSearchProvider = Depends(get_vector_search_provider),
    ranking_engine: MatchingRankingEngine = Depends(get_matching_ranking_engine),
) -> ProjectMatchingService:
    return ProjectMatchingService(
        project_repo=project_repo,
        embedding_provider=embedding_provider,
        vector_search_provider=vector_search_provider,
        ranking_engine=ranking_engine,
    )


def get_financial_rule_engine() -> FinancialRuleEngine:
    return FinancialRuleEngine()


async def get_financial_validation_service(
    project_repo: SQLAlchemyPastProjectRepository = Depends(get_project_repository),
    rule_engine: FinancialRuleEngine = Depends(get_financial_rule_engine),
) -> FinancialValidationService:
    return FinancialValidationService(
        project_repo=project_repo,
        rule_engine=rule_engine,
    )


def get_risk_engine() -> RiskEngine:
    return RiskEngine()


async def get_risk_service(
    tender_repo: SQLAlchemyTenderRepository = Depends(get_tender_repository),
    metadata_repo: SQLAlchemyTenderMetadataRepository = Depends(get_metadata_repository),
    risk_engine: RiskEngine = Depends(get_risk_engine),
) -> RiskService:
    return RiskService(
        tender_repo=tender_repo,
        metadata_repo=metadata_repo,
        risk_engine=risk_engine,
    )


def get_recommendation_rules_engine() -> RecommendationRulesEngine:
    return RecommendationRulesEngine()


async def get_tender_recommendation_service(
    tender_repo: SQLAlchemyTenderRepository = Depends(get_tender_repository),
    metadata_repo: SQLAlchemyTenderMetadataRepository = Depends(get_metadata_repository),
    boq_analytics_service: BOQAnalyticsService = Depends(get_boq_analytics_service),
    matching_service: ProjectMatchingService = Depends(get_project_matching_service),
    qualification_service: FinancialValidationService = Depends(get_financial_validation_service),
    risk_service: RiskService = Depends(get_risk_service),
    rules_engine: RecommendationRulesEngine = Depends(get_recommendation_rules_engine),
) -> TenderRecommendationService:
    return TenderRecommendationService(
        tender_repo=tender_repo,
        metadata_repo=metadata_repo,
        boq_analytics_service=boq_analytics_service,
        matching_service=matching_service,
        qualification_service=qualification_service,
        risk_service=risk_service,
        rules_engine=rules_engine,
    )


def get_llm_provider() -> GeminiLLMProvider:
    global _llm_provider_instance
    if "_llm_provider_instance" not in globals():
        _llm_provider_instance = GeminiLLMProvider()
    return _llm_provider_instance


async def get_ai_tender_analyst_service(
    recommendation_service: TenderRecommendationService = Depends(get_tender_recommendation_service),
    llm_provider: GeminiLLMProvider = Depends(get_llm_provider),
) -> AITenderAnalystService:
    return AITenderAnalystService(
        recommendation_service=recommendation_service,
        llm_provider=llm_provider,
    )


async def get_audit_repository(
    session: AsyncSession = Depends(get_db_session)
) -> SQLAlchemyAuditLogRepository:
    return SQLAlchemyAuditLogRepository(session)


async def get_audit_service(
    repo: SQLAlchemyAuditLogRepository = Depends(get_audit_repository)
) -> AuditLoggingService:
    return AuditLoggingService(repo)


async def get_review_repository(
    session: AsyncSession = Depends(get_db_session)
) -> SQLAlchemyTenderReviewRepository:
    return SQLAlchemyTenderReviewRepository(session)


async def get_tender_review_service(
    tender_repo: SQLAlchemyTenderRepository = Depends(get_tender_repository),
    metadata_repo: SQLAlchemyTenderMetadataRepository = Depends(get_metadata_repository),
    review_repo: SQLAlchemyTenderReviewRepository = Depends(get_review_repository),
    audit_service: AuditLoggingService = Depends(get_audit_service),
) -> TenderReviewService:
    return TenderReviewService(
        tender_repository=tender_repo,
        metadata_repository=metadata_repo,
        review_repository=review_repo,
        audit_service=audit_service
    )


# --- Authentication & Authorization (RBAC) Dependencies ---

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    session: AsyncSession = Depends(get_db_session)
) -> UserORM:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    if not token:
        raise credentials_exception

    payload = verify_access_token(token)
    if not payload:
        raise credentials_exception

    user_id = payload.get("sub")
    if not user_id:
        raise credentials_exception

    import uuid
    try:
        user_uuid = uuid.UUID(user_id)
    except (ValueError, AttributeError):
        raise credentials_exception

    try:
        stmt = select(UserORM).where(UserORM.id == user_uuid)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()
    except Exception:
        raise credentials_exception

    if user is None:
        raise credentials_exception
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )
        
    return user


class RoleChecker:
    def __init__(self, allowed_roles: list[UserRole]):
        self.allowed_roles = allowed_roles

    def __call__(self, current_user: UserORM = Depends(get_current_user)) -> UserORM:
        if not self.allowed_roles:
            return current_user
            
        min_allowed_level = min(role.level for role in self.allowed_roles)
        if current_user.role.level >= min_allowed_level:
            return current_user
            
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Insufficient permissions"
        )


def require_role(min_role: UserRole):
    allowed_roles = [r for r in UserRole if r.level >= min_role.level]
    return RoleChecker(allowed_roles)








