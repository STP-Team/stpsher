from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.database.repo.STP.achievement import AchievementsRepo
from infrastructure.database.repo.STP.product import ProductsRepo
from infrastructure.database.repo.STP.broadcast import BroadcastRepo
from infrastructure.database.repo.STP.schedule_log import ScheduleLogRepo
from infrastructure.database.repo.STP.transactions import TransactionRepo
from infrastructure.database.repo.STP.employee import EmployeeRepo
from infrastructure.database.repo.STP.purchase import PurchaseRepo


@dataclass
class MainRequestsRepo:
    """
    Repository for handling database operations. This class holds all the repositories for the database models.

    You can add more repositories as properties to this class, so they will be easily accessible.
    """

    session: AsyncSession

    @property
    def employee(self) -> EmployeeRepo:
        """
        The Employee repository sessions are required to manage user operations.
        """
        return EmployeeRepo(self.session)

    @property
    def upload(self) -> ScheduleLogRepo:
        """
        The ScheduleLogRepo repository sessions are required to manage user operations.
        """
        return ScheduleLogRepo(self.session)

    @property
    def product(self) -> ProductsRepo:
        """
        The ProductsRepo repository sessions are required to manage user operations.
        """
        return ProductsRepo(self.session)

    @property
    def purchase(self) -> PurchaseRepo:
        """
        The PurchaseRepo repository sessions are required to manage user operations.
        """
        return PurchaseRepo(self.session)

    @property
    def achievement(self) -> AchievementsRepo:
        """
        The AchievementsRepo repository sessions are required to manage user operations.
        """
        return AchievementsRepo(self.session)

    @property
    def transaction(self) -> TransactionRepo:
        """
        The TransactionRepo repository sessions are required to manage transactions.
        """
        return TransactionRepo(self.session)

    @property
    def broadcast(self) -> BroadcastRepo:
        """
        The BroadcastRepo repository sessions are required to manage broadcasts.
        """
        return BroadcastRepo(self.session)
