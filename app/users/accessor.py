import aiohttp


class UserAccessor:
    def __init__(self, store, token) -> None:
        self.store = store
        self.token = token
        self.base_url = f"https://api.telegram.org/bot{token}/"
        self.offset = None

    async def send_request(self, method, data=None):
        url = self.base_url + method
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=data) as response:
                return await response.json()

    async def poll(self):
        while True:
            updates = await self.send_request("getUpdates", {"offset": self.offset})
            for update in updates.get("result", []):
                chat_id = update["message"]["chat"]["id"]
                message_text = update["message"]["text"]

                await self.send_request("sendMessage", {"chat_id": chat_id, "text": message_text})

                self.offset = update["update_id"] + 1
