import typing
from logging import getLogger

from app.store.telegram_api.dataclasses import Message, UpdateObject

if typing.TYPE_CHECKING:
    from app.web.app import Application


class BotManager:
    def __init__(self, app: "Application"):
        self.app = app
        self.bot = None
        self.logger = getLogger("handler")

    async def handle_updates(self, updates: list[UpdateObject]):
        for update in updates:
            if update.message.text.startswith("/"):
                command = update.message.text.split()[0]
                await self.handle_command(command, update.message.from_id)
            else:
                await self.app.store.telegram_api.send_message(
                    Message(
                        chat_id=update.message.from_id,
                        text=update.message.text,
                    )
                )

    async def handle_command(self, command: str, user_id: int):
        if command == "/start":
            res = await self.app.store.users.get_by_id(user_id)
            if res is None:
                await self.app.store.users.create_user(user_id)
                await self.app.store.telegram_api.send_message(
                    Message(
                        chat_id=user_id,
                        text="Привет! Это игра Поле Чудес. Я вижу, ты здесь "
                             "впервые, с правилами можешь ознакомиться по "
                             "команде /rules. Давай сыграем! Для начала "
                             "игры напиши /play.",
                    )
                )
            else:
                await self.app.store.telegram_api.send_message(
                    Message(
                        chat_id=user_id,
                        text="Привет! А я тебя уже знаю! Если что, правила "
                             "доступны по команде /rules. Для начала игры "
                             "напиши /play.",
                    )
                )
