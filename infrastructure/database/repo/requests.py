from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.database.repo.achievement import AchievementsRepo
from infrastructure.database.repo.award import AwardsRepo
from infrastructure.database.repo.schedule_log import ScheduleLogRepo
from infrastructure.database.repo.user import UserRepo


@dataclass
class RequestsRepo:
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
    def achievement(self) -> AchievementsRepo:
        """
        The AchievementsRepo repository sessions are required to manage user operations.
        """
        return AchievementsRepo(self.session)
