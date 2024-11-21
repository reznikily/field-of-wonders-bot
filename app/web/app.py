from aiohttp.web import (
    Application as AiohttpApplication,
    Request as AiohttpRequest,
    View as AiohttpView,
)
from aiohttp_apispec import setup_aiohttp_apispec
from aiohttp_session import setup as session_setup
from aiohttp_session.cookie_storage import EncryptedCookieStorage

from app.admin.models import AdminModel
from app.store import Database, Store, setup_store
from app.web.config import setup_config
from app.web.logger import setup_logging
from app.web.mw import setup_middlewares
from app.web.routes import setup_routes

__all__ = ("Application",)


class Application(AiohttpApplication):
    config = None
    store = None
    database = None


class Request(AiohttpRequest):
    admin: AdminModel | None = None

    @property
    def app(self) -> Application:
        return super().app()


class View(AiohttpView):
    @property
    def request(self) -> Request:
        return super().request

    @property
    def database(self) -> Database:
        return self.request.app.database

    @property
    def store(self) -> Store:
        return self.request.app.store

    @property
    def data(self) -> dict:
        return self.request.get("data", {})


app = Application()


def setup_app(config_path: str) -> Application:
    setup_logging(app)
    setup_config(app, config_path)
    session_setup(app, EncryptedCookieStorage(app.config.session.key))
    setup_routes(app)
    setup_aiohttp_apispec(
        app,
        title="Telegram Field of Wonders Bot",
        url="/docs/json",
        swagger_path="/docs",
    )
    setup_middlewares(app)
    setup_store(app)
    return app
