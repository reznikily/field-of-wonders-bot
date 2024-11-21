from aiohttp.web_exceptions import HTTPForbidden, HTTPUnauthorized
from aiohttp_session import get_session, new_session

from app.admin.models import AdminModel
from app.web.app import Request
from app.web.utils import hash_password


class AuthRequiredMixin:
    @staticmethod
    async def auth_admin(
        request: Request, admin: AdminModel, data: dict
    ) -> AdminModel | None:
        if not data.get("login") or not data.get("password") or not admin:
            raise HTTPForbidden

        if (
            data.get("login") == admin.login
            and hash_password(data.get("password")) == admin.password
        ):
            session = await new_session(request)
            session["login"] = admin.login
            session["password"] = admin.password

            return AdminModel(id=admin.id, login=admin.login)

        raise HTTPForbidden

    @staticmethod
    async def check_auth_admin(request: Request) -> AdminModel | None:
        session = await get_session(request)
        login = session.get("login")
        password = session.get("password")

        if not login or not password:
            raise HTTPUnauthorized

        admin = await request.app.store.admins.get_by_login(login)
        if admin.password == password:
            return AdminModel(id=admin.id, login=admin.login)

        raise HTTPUnauthorized
