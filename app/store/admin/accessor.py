from sqlalchemy import insert, select

from app.admin.models import AdminModel
from app.base.base_accessor import BaseAccessor
from app.web.utils import hash_password


class AdminAccessor(BaseAccessor):
    async def get_by_login(self, login: str) -> AdminModel | None:
        if self.app.config.admin.login == login:
            return AdminModel(
                id=1,
                login=self.app.config.admin.login,
                password=hash_password(self.app.config.admin.password),
            )

        request = select(AdminModel).where(AdminModel.login == login)
        async with self.app.database.session as session:
            res = await session.execute(request)
            return res.first()

    async def create_admin(self, login: str, password: str) -> AdminModel:
        request = insert(AdminModel).values(
            login=login, password=hash_password(password)
        )
        async with self.app.database.session as session:
            res = await session.execute(request)
            res.all()

        return AdminModel(login=login, password=password)
