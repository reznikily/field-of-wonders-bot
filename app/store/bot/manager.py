import asyncio
import json
import typing
from logging import getLogger

from app.store.telegram_api.dataclasses import (
    CallbackAnswer,
    CallbackQuery,
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
        self.registration_tasks = {}
        self.game_tasks = {}
        self.game_states = {}
        self.input_events = {}

    async def handle_updates(self, updates: list[UpdateObject]) -> None:
        for update in updates:
            obj = update.object
            if update.type == "message":
                if obj.text.startswith("/"):
                    command = obj.text.split()[0].split("@")[0]
                    await self.handle_command(command, obj)
                else:
                    await self.handle_game_input(obj)
            elif update.type == "callback_query":
                await self.handle_callback_query(obj)

    async def handle_command(
        self, command: str, message: UpdateMessage
    ) -> None:
        if command == "/start":
            res = await self.app.store.users.get_by_id(message.from_id)
            if res is None:
                await self.app.store.users.create_user(
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
                    text="Правила игры:\n"
                    "1. После отправки команды /play начинается "
                    "регистрация на игру. На регистрацию отводится "
                    "всего 15 секунд. Для игры нужно минимум 2 игрока.\n"
                    "2. Каждый ход игрок может назвать букву или слово "
                    "целиком.\n"
                    "3. За каждую угаданную букву +10 очков.\n"
                    "4. За угаданное слово +100 очков.\n"
                    "5. На ход даётся 15 секунд.\n"
                    "6. При ошибке ход переходит следующему игроку.",
                )
            )
        elif command == "/play":
            game = await self.app.store.game.get_active_game_by_chat_id(
                message.chat_id
            )
            if game is None:
                await self.start_new_game(message)
            else:
                await self.app.store.telegram_api.send_message(
                    Message(
                        chat_id=message.chat_id,
                        text="В этом чате уже идёт игра!",
                    )
                )
        else:
            await self.app.store.telegram_api.send_message(
                Message(
                    chat_id=message.chat_id,
                    text="Прости, но таких команд не знаю :(",
                )
            )

    async def handle_callback_query(self, query: CallbackQuery) -> None:
        if query.data.startswith("participate"):
            game_id = int(query.data.split("_")[1])
            active_game = await self.app.store.game.get_active_game_by_chat_id(
                chat_id=query.chat_id
            )
            if active_game.id == game_id:
                if query.chat_id in self.registration_tasks:
                    await self.app.store.game.create_player(
                        user_id=query.from_id,
                        username=query.username,
                        game_id=game_id,
                    )
                    await self.app.store.telegram_api.send_message(
                        Message(
                            chat_id=query.chat_id,
                            text=f"@{query.username} участвует!",
                        )
                    )
                else:
                    await self.app.store.telegram_api.send_callback_answer(
                        CallbackAnswer(
                            callback_id=query.id,
                            text="Извините, регистрация уже закончена!",
                        )
                    )

    async def start_new_game(self, message: UpdateMessage):
        await self.app.store.game.create_game(message.chat_id)
        game = await self.app.store.game.get_active_game_by_chat_id(
            message.chat_id
        )
        user = await self.app.store.users.get_by_id(message.from_id)
        if user is None:
            await self.app.store.users.create_user(
                message.from_id, message.username
            )

        registration_task = asyncio.create_task(
            self.handle_registration_period(game.id, message.chat_id)
        )
        self.registration_tasks[message.chat_id] = registration_task

        reply_markup = {
            "inline_keyboard": [
                [
                    {
                        "text": "Участвовать",
                        "callback_data": f"participate_{game.id}",
                    }
                ]
            ]
        }
        await self.app.store.telegram_api.send_message(
            Message(
                chat_id=message.chat_id,
                text="Начинаем игру! Правила доступны по команде "
                "/rules. Даю 15 секунд на то, чтобы "
                "зарегистрироваться!",
            ),
            reply_markup=json.dumps(reply_markup),
        )

    async def handle_registration_period(self, game_id: int, chat_id: int):
        try:
            await asyncio.sleep(5)
            await self.app.store.telegram_api.send_message(
                Message(
                    chat_id=chat_id,
                    text="Осталось 10 секунд!",
                )
            )
            await asyncio.sleep(5)
            await self.app.store.telegram_api.send_message(
                Message(
                    chat_id=chat_id,
                    text="Осталось 5 секунд!",
                )
            )
            await asyncio.sleep(5)

            players = await self.app.store.game.get_players_by_game_id(game_id)
            if len(players) < 2:
                await self.app.store.telegram_api.send_message(
                    Message(
                        chat_id=chat_id,
                        text="Недостаточно игроков для начала игры "
                        "(минимум 2).",
                    )
                )
                await self.app.store.game.end_game(game_id)
                return

            await self.app.store.telegram_api.send_message(
                Message(
                    chat_id=chat_id,
                    text="Начинаем!",
                )
            )

            await self.start_game_round(chat_id, game_id)

        finally:
            if chat_id in self.registration_tasks:
                del self.registration_tasks[chat_id]

    async def start_game_round(self, chat_id: int, game_id: int):
        game = await self.app.store.game.get_game_by_id(game_id)
        question = await self.app.store.game.get_question_by_id(
            game.question_id
        )
        players = await self.app.store.game.get_players_by_game_id(game_id)

        word = question.answer.upper()

        self.game_states[chat_id] = {
            "word": word,
            "word_state": 0,
            "current_player_idx": 0,
            "players": players,
            "scores": {player.user_id: player.points for player in players},
            "game_id": game_id,
            "waiting_for_input": False,
        }

        self.input_events[chat_id] = asyncio.Event()

        game_task = asyncio.create_task(self.run_game(chat_id))
        self.game_tasks[chat_id] = game_task

    async def run_game(self, chat_id: int):
        try:
            game_state = self.game_states[chat_id]

            masked_word = self.get_masked_word(
                game_state["word"], game_state["word_state"]
            )
            await self.app.store.telegram_api.send_message(
                Message(
                    chat_id=chat_id,
                    text=f"Слово: {masked_word}\nДлина слова: "
                    f"{len(game_state['word'])} букв",
                )
            )

            while not self.is_game_over(chat_id):
                current_player = game_state["players"][
                    game_state["current_player_idx"]
                ]
                await self.app.store.telegram_api.send_message(
                    Message(
                        chat_id=chat_id,
                        text=f"Ход игрока @{current_player.username}. "
                        f"Назовите букву или слово целиком:",
                    ),
                    reply_markup=json.dumps({"force_reply": True}),
                )

                game_state["waiting_for_input"] = True

                try:
                    await asyncio.wait_for(
                        self.input_events[chat_id].wait(), timeout=15
                    )
                    self.input_events[chat_id].clear()
                except TimeoutError:
                    await self.app.store.telegram_api.send_message(
                        Message(
                            chat_id=chat_id,
                            text=f"@{current_player.username} "
                            f"не успел(а) ответить. "
                            f"Ход переходит к следующему игроку.",
                        )
                    )
                    await self.next_player(chat_id)
                finally:
                    game_state["waiting_for_input"] = False

        except Exception:
            self.logger.error("Error in game task.")
            await self.app.store.telegram_api.send_message(
                Message(
                    chat_id=chat_id,
                    text="Произошла ошибка в игре. Игра остановлена.",
                )
            )
        finally:
            await self.end_game(chat_id)

    async def handle_game_input(self, message: UpdateMessage) -> None:
        chat_id = message.chat_id
        if chat_id not in self.game_states:
            return

        game_state = self.game_states[chat_id]
        if not game_state["waiting_for_input"]:
            return

        current_player = game_state["players"][game_state["current_player_idx"]]
        if message.from_id != current_player.user_id:
            return

        guess = message.text.strip().upper()
        valid_input = False

        if len(guess) == 1:
            if self.is_letter_revealed(
                game_state["word"], game_state["word_state"], guess
            ):
                await self.app.store.telegram_api.send_message(
                    Message(chat_id=chat_id, text="Эта буква уже была названа!")
                )
                return

            new_word_state = self.reveal_letter(
                game_state["word"], game_state["word_state"], guess
            )
            if new_word_state != game_state["word_state"]:
                game_state["word_state"] = new_word_state
                points = self.count_letter(game_state["word"], guess) * 10
                game_state["scores"][current_player.user_id] += points

                await self.app.store.game.update_word_state(
                    game_state["game_id"], new_word_state
                )
                await self.app.store.game.update_player_points(
                    current_player.id,
                    game_state["scores"][current_player.user_id],
                )

                masked_word = self.get_masked_word(
                    game_state["word"], game_state["word_state"]
                )
                await self.app.store.telegram_api.send_message(
                    Message(
                        chat_id=chat_id,
                        text=f"Буква '{guess}' есть в слове! +{points} очков\n"
                        f"Слово: {masked_word}",
                    )
                )
                valid_input = True
            else:
                await self.app.store.telegram_api.send_message(
                    Message(
                        chat_id=chat_id, text=f"Буквы '{guess}' нет в слове!"
                    )
                )
                await self.next_player(chat_id)
                valid_input = True
        elif guess == game_state["word"]:
            game_state["scores"][current_player.user_id] += 100
            game_state["word_state"] = (1 << len(game_state["word"])) - 1
            await self.end_game(chat_id, current_player)
            valid_input = True
        else:
            await self.app.store.telegram_api.send_message(
                Message(chat_id=chat_id, text="Неверное слово!")
            )
            await self.next_player(chat_id)
            valid_input = True

        if valid_input and chat_id in self.input_events:
            self.input_events[chat_id].set()

    async def next_player(self, chat_id: int):
        game_state = self.game_states[chat_id]
        current_player = game_state["players"][game_state["current_player_idx"]]

        next_idx = (game_state["current_player_idx"] + 1) % len(
            game_state["players"]
        )
        next_player = game_state["players"][next_idx]

        await self.app.store.game.update_next_player(
            current_player.id, next_player.id
        )
        game_state["current_player_idx"] = next_idx

    @staticmethod
    def get_masked_word(word: str, word_state: int) -> str:
        return " ".join(
            letter if word_state & (1 << i) else "_"
            for i, letter in enumerate(word)
        )

    def is_game_over(self, chat_id: int) -> bool:
        game_state = self.game_states[chat_id]
        return game_state["word_state"] == (1 << len(game_state["word"])) - 1

    @staticmethod
    def is_letter_revealed(word: str, word_state: int, letter: str) -> bool:
        for i, char in enumerate(word):
            if char == letter and word_state & (1 << i):
                return True
        return False

    @staticmethod
    def reveal_letter(word: str, word_state: int, letter: str) -> int:
        new_state = word_state
        for i, char in enumerate(word):
            if char == letter:
                new_state |= 1 << i
        return new_state

    @staticmethod
    def count_letter(word: str, letter: str) -> int:
        return word.count(letter)

    async def end_game(self, chat_id: int, winner=None):
        try:
            game_state = self.game_states[chat_id]

            for player in game_state["players"]:
                await self.app.store.game.update_player_points(
                    player.id, game_state["scores"][player.user_id]
                )
                await self.app.store.game.update_player_status(
                    player.id, in_game=False
                )

            scores_text = "Финальный счёт:\n" + "\n".join(
                f"@{player.username}: "
                f"{game_state['scores'][player.user_id]} очков"
                for player in game_state["players"]
            )

            if winner:
                await self.app.store.telegram_api.send_message(
                    Message(
                        chat_id=chat_id,
                        text=f"Поздравляем! @{winner.username} "
                        f"угадал(а) слово: {game_state['word']}\n\n"
                        f"{scores_text}",
                    )
                )
                await self.app.store.game.end_game(
                    game_id=game_state["game_id"],
                    winner_id=winner.user_id,
                    word_state=(1 << len(game_state["word"])) - 1,
                )
            else:
                await self.app.store.telegram_api.send_message(
                    Message(
                        chat_id=chat_id,
                        text=f"Игра окончена! Загаданное слово было: "
                        f"{game_state['word']}\n\n"
                        f"{scores_text}",
                    )
                )
                await self.app.store.game.end_game(
                    game_id=game_state["game_id"],
                    winner_id=None,
                    word_state=(1 << len(game_state["word"])) - 1,
                )

            if chat_id in self.game_tasks:
                self.game_tasks[chat_id].cancel()
                del self.game_tasks[chat_id]

            if chat_id in self.game_states:
                del self.game_states[chat_id]

        except Exception:
            self.logger.error("Error ending game.")
            await self.app.store.telegram_api.send_message(
                Message(
                    chat_id=chat_id,
                    text="Произошла ошибка при завершении игры.",
                )
            )
