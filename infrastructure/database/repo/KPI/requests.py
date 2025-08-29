from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.database.repo.KPI.head_month_kpi import HeadMonthKPIRepo


@dataclass
class KPIRequestsRepo:
    """
    Repository for handling database operations. This class holds all the repositories for the database models.

    You can add more repositories as properties to this class, so they will be easily accessible.
    """

    session: AsyncSession

    @property
    def head_month_kpi(self) -> HeadMonthKPIRepo:
        """
        The HeadMonthKPIRepo repository sessions are required to manage head kpi operations.
        """
        return HeadMonthKPIRepo(self.session)
