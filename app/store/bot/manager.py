import asyncio
import typing
from logging import getLogger

from app.store.telegram_api.dataclasses import (
    Message,
    UpdateMessage,
    UpdateObject,
)

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
                command = update.message.text.split()[0].split("@")[0]
                await self.handle_command(command, update.message)

    async def handle_command(self, command: str, message: UpdateMessage):
        if command == "/start":
            res = await self.app.store.users.get_by_id(message.from_id)
            if res is None:
                user = await self.app.store.users.create_user(
                    message.from_id, message.username
                )
                await self.app.store.telegram_api.send_message(
                    Message(
                        chat_id=message.chat_id,
                        text=f"@{message.username}, привет! Это игра Поле "
                        f"Чудес. Я вижу, ты здесь впервые, с правилами "
                        f"можешь ознакомиться по команде /rules. Давай "
                        f"сыграем! Для начала игры напиши /play.",
                    )
                )
            else:
                await self.app.store.telegram_api.send_message(
                    Message(
                        chat_id=message.chat_id,
                        text=f"Привет, @{message.username}! А я тебя уже знаю!"
                        f" Если что, правила доступны по команде /rules. "
                        f"Для начала игры напиши /play.",
                    )
                )
        elif command == "/rules":
            await self.app.store.telegram_api.send_message(
                Message(
                    chat_id=message.chat_id,
                    text="Скоро здесь появятся правила...",
                )
            )
        elif command == "/play":
            game = await self.app.store.game.get_active_game_by_chat_id(
                message.chat_id
            )
            if game is None:
                await self.app.store.game.create_game(message.chat_id)
                game = await self.app.store.game.get_active_game_by_chat_id(
                    message.chat_id
                )
                user = await self.app.store.users.get_by_id(message.from_id)
                if user is None:
                    await self.app.store.users.create_user(
                        message.from_id, message.username
                    )
                await self.app.store.telegram_api.send_message(
                    Message(
                        chat_id=message.chat_id,
                        text="Начинаем игру! Правила доступны по команде "
                        "/rules. Даю 15 секунд на то, чтобы "
                        "зарегистрироваться!",
                    )
                )
                await asyncio.sleep(5)
                await self.app.store.telegram_api.send_message(
                    Message(
                        chat_id=message.chat_id,
                        text="Осталось 10 секунд!",
                    )
                )
                await asyncio.sleep(5)
                await self.app.store.telegram_api.send_message(
                    Message(
                        chat_id=message.chat_id,
                        text="Осталось 5 секунд!",
                    )
                )
                await asyncio.sleep(5)
                await self.app.store.telegram_api.send_message(
                    Message(
                        chat_id=message.chat_id,
                        text="Начинаем!",
                    )
                )
        else:
            await self.app.store.telegram_api.send_message(
                Message(
                    chat_id=message.chat_id,
                    text="Прости, но таких команд не знаю :(",
                )
            )
