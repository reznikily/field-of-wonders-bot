from aiohttp.web_exceptions import HTTPBadRequest, HTTPForbidden
from aiohttp_apispec import docs, request_schema, response_schema
from aiohttp_session import get_session

from app.admin.schemes import AdminResponseSchema, AdminSchema
from app.web.app import View
from app.web.mixins import AuthRequiredMixin
from app.web.utils import hash_password, json_response


class AdminLoginView(View):
    @docs(
        tags=["Admin"],
        summary="Login admin",
        description="Login admin"
    )
    @request_schema(AdminSchema)
    @response_schema(AdminSchema, 200)
    async def post(self):
        data = await self.request.json()
        try:
            login = data["login"]
            password = data["password"]
        except KeyError:
            return HTTPBadRequest

        password_hash = hash_password(password)

        admin = await self.request.app.store.admins.get_by_login(login=login)
        if not admin:
            raise HTTPForbidden

        session = await get_session(self.request)
        session["token"] = self.request.app.config.session.key

        if login == admin.login and password_hash == admin.password:
            session["admin"] = {}
            session["admin"].setdefault("id", admin.id)
            session["admin"].setdefault("login", admin.login)

            raw_admin = AdminResponseSchema().dump(admin)
            return json_response(data=raw_admin)

        raise HTTPForbidden


class AdminCurrentView(AuthRequiredMixin, View):
    @docs(
        tags=["Admin"],
        summary="Admin current",
        description="Get admin current data",
    )
    @response_schema(AdminSchema, 200)
    async def get(self):
        session = await get_session(self.request)
        admin = session.get("admin")
        return json_response(data=AdminSchema().dump(admin))
