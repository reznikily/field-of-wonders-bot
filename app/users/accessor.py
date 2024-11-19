from sqlalchemy import insert, select

from app.base.base_accessor import BaseAccessor
from app.users.models import UserModel


class UserAccessor(BaseAccessor):
    async def create_user(self, user_id: int, username: str) -> None:
        request = insert(UserModel).values(
            id=user_id, username=username, role="player", score=0, points=0
        )
        async with self.app.database.session as session:
            await session.execute(request)
            await session.commit()

    async def get_by_id(self, user_id: int) -> UserModel | None:
        request = select(UserModel).where(UserModel.id == user_id)
        async with self.app.database.session as session:
            res = await session.execute(request)
            row = res.first()
            if row is not None:
                return row[0]

        return None
