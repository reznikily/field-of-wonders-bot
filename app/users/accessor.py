import typing

from sqlalchemy import insert, select

from app.base.base_accessor import BaseAccessor
from app.users.models import UserModel

if typing.TYPE_CHECKING:
    from app.web.app import Application


class UserAccessor(BaseAccessor):
    def __init__(self, app: "Application", *args, **kwargs) -> None:
        super().__init__(app, *args, **kwargs)

    async def connect(self, app: "Application") -> None:
        self.app = app

    async def create_user(self, user_id: int) -> UserModel:
        request = insert(UserModel).values(
            id=user_id, role="player", score=0, points=0
        )
        async with self.app.database.session as session:
            await session.execute(request)
            await session.commit()

        return UserModel(id=user_id, role="player", score=0, points=0)

    async def get_by_id(self, user_id: int) -> UserModel | None:
        request = select(UserModel)
        async with self.app.database.session as session:
            res = await session.execute(request)

            for user in res:
                if user[0].id == user_id:
                    return user[0]

        return None
