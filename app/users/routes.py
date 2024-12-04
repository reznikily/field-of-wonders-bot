from aiohttp.web_app import Application

__all__ = ("setup_routes",)

from app.users.views.list_users import UserListView
from app.web.app import app


def setup_routes(application: Application):
    app.router.add_view("/users.list_users", UserListView)
