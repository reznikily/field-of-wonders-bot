import typing

from aiohttp.client import ClientSession

from app.base.base_accessor import BaseAccessor
from app.store.telegram_api.dataclasses import (
    Message,
    UpdateMessage,
    UpdateObject,
)
from app.store.telegram_api.poller import Poller

if typing.TYPE_CHECKING:
    from app.web.app import Application

API_PATH = "https://api.telegram.org/"


class TelegramApiAccessor(BaseAccessor):
    def __init__(self, app: "Application", *args, **kwargs):
        super().__init__(app, *args, **kwargs)

        self.token: str | None = None
        self.offset: int | None = None
        self.session: ClientSession | None = None
        self.poller: Poller | None = None

    async def connect(self, app: "Application") -> None:
        self.session = ClientSession()

        self.token = app.config.bot.token
        self.poller = Poller(app.store)
        self.logger.info("start polling")
        self.poller.start()

    async def disconnect(self, app: "Application") -> None:
        if self.poller:
            await self.poller.stop()

    @staticmethod
    def _build_url(token: str, method: str) -> str:
        return API_PATH + f"bot{token}/{method}"

    async def poll(self):
        async with self.session.get(
            self._build_url(token=self.token, method="getUpdates"),
            data={"offset": self.offset},
        ) as response:
            data = await response.json()
            self.logger.info(data)

            updates = []
            for update in data.get("result", []):
                self.offset = update["update_id"] + 1
                if "message" in update:
                    updates.append(
                        UpdateObject(
                            id=update["update_id"],
                            message=UpdateMessage(
                                id=update["message"]["message_id"],
                                from_id=update["message"]["from"]["id"],
                                chat_id=update["message"]["chat"]["id"],
                                username=update["message"]["from"]["username"],
                                text=update["message"]["text"],
                            ),
                        )
                    )

            await self.app.store.bots_manager.handle_updates(updates)

    async def send_message(self, message: Message) -> None:
        async with self.session.post(
            self._build_url(token=self.token, method="sendMessage"),
            data={"chat_id": message.chat_id, "text": message.text},
        ) as response:
            data = await response.json()
            self.logger.info(data)
