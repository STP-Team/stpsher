from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.database.repo.STP.achievement import AchievementsRepo
from infrastructure.database.repo.STP.award import AwardsRepo
from infrastructure.database.repo.STP.broadcast import BroadcastRepo
from infrastructure.database.repo.STP.schedule_log import ScheduleLogRepo
from infrastructure.database.repo.STP.transactions import TransactionRepo
from infrastructure.database.repo.STP.user import UserRepo
from infrastructure.database.repo.STP.user_award import UserAwardsRepo


@dataclass
class MainRequestsRepo:
    """
    Repository for handling database operations. This class holds all the repositories for the database models.

    You can add more repositories as properties to this class, so they will be easily accessible.
    """

    session: AsyncSession

    @property
    def user(self) -> UserRepo:
        """
        The User repository sessions are required to manage user operations.
        """
        return UserRepo(self.session)

    @property
    def upload(self) -> ScheduleLogRepo:
        """
        The ScheduleLogRepo repository sessions are required to manage user operations.
        """
        return ScheduleLogRepo(self.session)

    @property
    def award(self) -> AwardsRepo:
        """
        The AwardsRepo repository sessions are required to manage user operations.
        """
        return AwardsRepo(self.session)

    @property
    def user_award(self) -> UserAwardsRepo:
        """
        The UserAwardsRepo repository sessions are required to manage user operations.
        """
        return UserAwardsRepo(self.session)

    @property
    def achievement(self) -> AchievementsRepo:
        """
        The AchievementsRepo repository sessions are required to manage user operations.
        """
        return AchievementsRepo(self.session)

    @property
    def transaction(self) -> TransactionRepo:
        """
        The UserAchievementsRepo repository sessions are required to manage transactions.
        """
        return TransactionRepo(self.session)

    @property
    def broadcast(self) -> BroadcastRepo:
        """
        The BroadcastRepo repository sessions are required to manage broadcasts.
        """
        return BroadcastRepo(self.session)
