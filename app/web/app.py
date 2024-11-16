from aiohttp.web import Application as AiohttpApplication

from app.store import setup_store
from app.web.config import setup_config
from app.web.logger import setup_logging
from app.web.routes import setup_routes

__all__ = ("Application",)


class Application(AiohttpApplication):
    config = None
    store = None
    database = None


app = Application()


def setup_app(config_path: str) -> Application:
    setup_logging(app)
    setup_routes(app)
    setup_config(app, config_path)
    setup_store(app)
    return app
