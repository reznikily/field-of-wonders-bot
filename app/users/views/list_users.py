from aiohttp_apispec import response_schema

from app.users.schema import (
    ListUserSchema,
    UserSchema,
)
from app.web.app import View
from app.web.mixins import AuthRequiredMixin
from app.web.utils import json_response


class UserListView(AuthRequiredMixin, View):
    @response_schema(ListUserSchema, 200)
    async def get(self):
        users = await self.request.app.store.users.list_users()
        if not users:
            return json_response(data={"users": users})

        raw_users = [UserSchema().dump(user[0] for user in users)]
        return json_response(data={"users": raw_users})
