import asyncio

import yaml
from aiohttp.web import (
    Application as AiohttpApplication,
)

from .routes import setup_routes

__all__ = ("Application",)

from ..store import Store


class Application(AiohttpApplication):
    config = None
    store = None
    database = None


app = Application()


# async def start_polling(application: Application):
#     asyncio.create_task(application.store.user.poll())


def setup_app(config_path: str) -> Application:
    with open(config_path) as f:
        config = yaml.safe_load(f)
        app.config = config

    token = config["telegram"]["token"]
    app.store = Store(token)

    setup_routes(app)

    app.on_startup.append(app.store.user.poll())

    return app
