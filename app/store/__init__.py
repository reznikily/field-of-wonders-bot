import typing

__all__ = ("Store",)

from app.store.database.database import Database

if typing.TYPE_CHECKING:
    from app.web.app import Application


class Store:
    def __init__(self, app: "Application"):
        from app.game.accessor import GameAccessor
        from app.store.admin.accessor import AdminAccessor
        from app.store.bot.manager import BotManager
        from app.store.telegram_api.accessor import TelegramApiAccessor
        from app.users.accessor import UserAccessor

        self.admins = AdminAccessor(app)
        self.users = UserAccessor(app)
        self.game = GameAccessor(app)
        self.telegram_api = TelegramApiAccessor(app)
        self.bots_manager = BotManager(app)


def setup_store(app: "Application") -> None:
    app.database = Database(app)
    app.on_startup.append(app.database.connect)
    app.on_cleanup.append(app.database.disconnect)
    app.store = Store(app)
