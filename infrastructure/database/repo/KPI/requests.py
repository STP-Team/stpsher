from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.database.repo.KPI.head_premium import HeadPremiumRepo
from infrastructure.database.repo.KPI.spec_day_kpi import SpecDayKPIRepo
from infrastructure.database.repo.KPI.spec_month_kpi import SpecMonthKPIRepo
from infrastructure.database.repo.KPI.spec_premium import SpecPremiumRepo
from infrastructure.database.repo.KPI.spec_week_kpi import SpecWeekKPIRepo


@dataclass
class KPIRequestsRepo:
    """
    Repository for handling database operations. This class holds all the repositories for the database models.

    You can add more repositories as properties to this class, so they will be easily accessible.
    """

    session: AsyncSession

    @property
    def head_premium(self) -> HeadPremiumRepo:
        """
        The HeadPremiumRepo repository sessions are required to manage head premium operations.
        """
        return HeadPremiumRepo(self.session)

    @property
    def spec_day_kpi(self) -> SpecDayKPIRepo:
        """
        The SpecDayKPIRepo repository sessions are required to manage specialist daily kpi operations.
        """
        return SpecDayKPIRepo(self.session)

    @property
    def spec_week_kpi(self) -> SpecWeekKPIRepo:
        """
        The SpecWeekKPIRepo repository sessions are required to manage specialist weekly kpi operations.
        """
        return SpecWeekKPIRepo(self.session)

    @property
    def spec_month_kpi(self) -> SpecMonthKPIRepo:
        """
        The SpecMonthKPIRepo repository sessions are required to manage specialist monthly kpi operations.
        """
        return SpecMonthKPIRepo(self.session)

    @property
    def spec_premium(self) -> SpecPremiumRepo:
        """
        The SpecPremiumRepo repository sessions are required to manage specialist premium operations.
        """
        return SpecPremiumRepo(self.session)
