from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.database.repo.schedule_log import ScheduleLogRepo
from infrastructure.database.repo.users import UserRepo


@dataclass
class RequestsRepo:
    """
    Repository for handling database operations. This class holds all the repositories for the database models.

    You can add more repositories as properties to this class, so they will be easily accessible.
    """

    session: AsyncSession

    @property
    def users(self) -> UserRepo:
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
