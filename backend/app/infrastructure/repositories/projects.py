import datetime
from decimal import Decimal
from typing import List, Optional, Tuple
from pydantic import UUID4
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models import PastProject
from app.domain.repositories import IPastProjectRepository
from app.infrastructure.db.models import PastProjectORM


def to_domain_project(orm: PastProjectORM) -> PastProject:
    return PastProject(
        id=orm.id,
        project_name=orm.project_name,
        client=orm.client,
        project_value=orm.project_value,
        completion_date=orm.completion_date,
        domain=orm.domain,
        location=orm.location,
        document_type=orm.document_type,
        document_path=orm.document_path,
        created_at=orm.created_at,
        updated_at=orm.updated_at,
    )


class SQLAlchemyPastProjectRepository(IPastProjectRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def add(self, project: PastProject) -> PastProject:
        orm = PastProjectORM(
            id=project.id,
            project_name=project.project_name,
            client=project.client,
            project_value=project.project_value,
            completion_date=project.completion_date,
            domain=project.domain,
            location=project.location,
            document_type=project.document_type,
            document_path=project.document_path,
            created_at=project.created_at,
            updated_at=project.updated_at,
        )
        self.session.add(orm)
        await self.session.flush()
        return to_domain_project(orm)

    async def get_by_id(self, id: UUID4) -> Optional[PastProject]:
        stmt = select(PastProjectORM).where(PastProjectORM.id == id)
        result = await self.session.execute(stmt)
        orm = result.scalar_one_or_none()
        if orm:
            return to_domain_project(orm)
        return None

    async def list(
        self,
        skip: int = 0,
        limit: int = 10,
        search: Optional[str] = None,
        domain: Optional[str] = None,
        location: Optional[str] = None,
        min_value: Optional[Decimal] = None,
    ) -> Tuple[List[PastProject], int]:
        # Build query
        stmt = select(PastProjectORM)
        count_stmt = select(func.count(PastProjectORM.id))

        filters = []
        if search:
            search_filter = or_(
                PastProjectORM.project_name.ilike(f"%{search}%"),
                PastProjectORM.client.ilike(f"%{search}%")
            )
            filters.append(search_filter)

        if domain:
            filters.append(PastProjectORM.domain == domain)

        if location:
            filters.append(PastProjectORM.location == location)

        if min_value is not None:
            filters.append(PastProjectORM.project_value >= min_value)

        if filters:
            stmt = stmt.where(*filters)
            count_stmt = count_stmt.where(*filters)

        # Execute count
        count_result = await self.session.execute(count_stmt)
        total_count = count_result.scalar() or 0

        # Execute pagination list
        stmt = stmt.order_by(PastProjectORM.created_at.desc()).offset(skip).limit(limit)
        result = await self.session.execute(stmt)
        orms = result.scalars().all()

        return [to_domain_project(orm) for orm in orms], total_count

    async def get_capabilities(self) -> List[dict]:
        # Count, sum, max aggregated per domain
        stmt = select(
            PastProjectORM.domain,
            func.count(PastProjectORM.id).label("project_count"),
            func.sum(PastProjectORM.project_value).label("total_value"),
            func.max(PastProjectORM.project_value).label("max_value")
        ).group_by(PastProjectORM.domain)

        result = await self.session.execute(stmt)
        aggregates = result.all()

        # Unique locations per domain
        loc_stmt = select(PastProjectORM.domain, PastProjectORM.location).distinct()
        loc_result = await self.session.execute(loc_stmt)
        
        locations_by_domain = {}
        for row in loc_result.all():
            domain_name = row[0]
            loc_name = row[1]
            if domain_name not in locations_by_domain:
                locations_by_domain[domain_name] = []
            locations_by_domain[domain_name].append(loc_name)

        capabilities = []
        for agg in aggregates:
            domain_name = agg.domain
            capabilities.append({
                "domain": domain_name,
                "project_count": agg.project_count,
                "total_value": agg.total_value or Decimal("0.00"),
                "max_value": agg.max_value or Decimal("0.00"),
                "locations": locations_by_domain.get(domain_name, [])
            })
        return capabilities
