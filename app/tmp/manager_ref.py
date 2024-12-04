import asyncio
import json
import random
import traceback
import typing
from dataclasses import dataclass, field
from logging import getLogger
from typing import Dict, List, Optional, Set, Tuple

from app.store.telegram_api.dataclasses import (
    CallbackAnswer,
    CallbackQuery,
    Message,
    UpdateMessage,
    UpdateObject,
)

if typing.TYPE_CHECKING:
    from app.web.app import Application


@dataclass
class GameConfig:
    sectors: List[typing.Union[str, int]] = field(
        default_factory=lambda: [
            "x2",
            "b",
            0,
            350,
            400,
            450,
            500,
            600,
            650,
            700,
            750,
            800,
            850,
            950,
            1000,
        ]
    )
    registration_time: int = 15
    input_timeout: int = 30


class GameStateManager:
    def __init__(self, game_config: GameConfig = GameConfig()):
        self.game_states: Dict[int, Dict] = {}
        self.input_events: Dict[int, asyncio.Event] = {}
        self.config = game_config

    def create_game_state(
        self,
        chat_id: int,
        game_id: int,
        question: str,
        word: str,
        players: List[Tuple],
    ) -> None:
        self.game_states[chat_id] = {
            "question": question,
            "word": word.upper(),
            "word_state": 0,
            "current_player_idx": 0,
            "current_sector": -1,
            "is_guessing_word": False,
            "used_letters": set(),
            "players": players,
            "scores": {
                player.user_id: player.points for player, user in players
            },
            "game_id": game_id,
            "is_waiting_for_input": False,
        }
        self.input_events[chat_id] = asyncio.Event()

    def get_game_state(self, chat_id: int) -> Optional[Dict]:
        return self.game_states.get(chat_id)

    def clear_game_state(self, chat_id: int) -> None:
        if chat_id in self.game_states:
            del self.game_states[chat_id]
        if chat_id in self.input_events:
            del self.input_events[chat_id]

    def question(self, chat_id: int):
        return self.game_states[chat_id]["question"]

    def word(self, chat_id: int):
        return self.game_states[chat_id]["word"]

    def word_state(self, chat_id: int):
        return self.game_states[chat_id]["word_state"]

    def current_player_idx(self, chat_id: int):
        return self.game_states[chat_id]["current_player_idx"]

    def current_sector(self, chat_id: int):
        return self.game_states[chat_id]["current_sector"]

    def is_guessing_word(self, chat_id: int):
        return self.game_states[chat_id]["is_guessing_word"]

    def used_letters(self, chat_id: int):
        return self.game_states[chat_id]["used_letters"]

    def players(self, chat_id: int):
        return self.game_states[chat_id]["players"]

    def scores(self, chat_id: int):
        return self.game_states[chat_id]["scores"]

    def game_id(self, chat_id: int):
        return self.game_states[chat_id]["game_id"]

    def is_waiting_for_input(self, chat_id: int):
        return self.game_states[chat_id]["is_waiting_for_input"]

    def set_guessing_word(self, chat_id: int, value: bool):
        self.game_states[chat_id]["is_guessing_word"] = value

    def set_input_event(self, chat_id: int):
        self.input_events[chat_id].set()

    def set_current_sector(self, chat_id: int, value: int):
        self.game_states[chat_id]["current_sector"] = value


class GameLogic:
    def __init__(self, game_config: GameConfig = GameConfig()):
        self.config = game_config

    @staticmethod
    def get_masked_word(word: str, word_state: int) -> str:
        return " ".join(
            letter if word_state & (1 << i) else "_"
            for i, letter in enumerate(word)
        )

    @staticmethod
    def is_game_over(word: str, word_state: int) -> bool:
        return word_state == (1 << len(word)) - 1

    @staticmethod
    def is_letter_revealed(word: str, word_state: int, letter: str) -> bool:
        return any(
            char == letter and word_state & (1 << i)
            for i, char in enumerate(word)
        )

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

    def calculate_points(
        self, current_sector: int, guessed_letters: int, current_points: int
    ) -> int:
        if current_sector == 0:  # x2 sector
            return current_points * (guessed_letters + 1)
        elif current_sector > 1:  # numeric sector
            return current_points + (
                guessed_letters * self.config.sectors[current_sector]
            )
        return current_points

    def random_sector(self):
        return random.randint(0, len(self.config.sectors) - 1)


class BotManager:
    def __init__(
        self,
        app: "Application",
        game_state: GameStateManager,
        game_logic: GameLogic,
    ):
        self.app = app
        self.game_state = game_state
        self.game_logic = game_logic
        self.logger = getLogger("handler")
        self.registration_tasks: Dict[int, asyncio.Task] = {}
        self.game_tasks: Dict[int, asyncio.Task] = {}

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
        command_handlers = {
            "/start": self._handle_start,
            "/rules": self._handle_rules,
            "/play": self._handle_play,
            "/profile": self._handle_profile,
            "/question": self._handle_question,
            "/used": self._handle_used,
            "/stop": self._handle_stop,
        }

        handler = command_handlers.get(command)
        if handler:
            await handler(message)
        else:
            await self.app.store.telegram_api.send_message(
                Message(
                    chat_id=message.chat_id,
                    text="Простите, но таких команд не знаю :(",
                )
            )

    async def _handle_start(self, message: UpdateMessage):
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
                    f"можешь ознакомиться по команде /rules. По "
                    f"команде /rules можешь посмотреть свою "
                    f"статистику. Давай сыграем! Для начала "
                    f"игры напиши /play.",
                )
            )
        else:
            await self.app.store.telegram_api.send_message(
                Message(
                    chat_id=message.chat_id,
                    text=f"Привет, @{message.username}! А я Вас "
                    f"уже знаю! Если что, правила доступны "
                    f"по команде /rules. "
                    f"Для начала игры напиши /play.",
                )
            )

    async def _handle_rules(self, message: UpdateMessage):
        await self.app.store.telegram_api.send_message(
            Message(
                chat_id=message.chat_id,
                text="Правила игры:\n"
                "После отправки команды /play начинается "
                "регистрация на игру. На регистрацию отводится "
                "всего 15 секунд. Для игры нужно минимум 2 игрока. "
                "В начале каждого хода крутится барабан. На "
                "барабане могут быть следующие сектора: x2, Б, "
                "0, 350, 400, 450, 500, 600, 650, 700, 750, 800, "
                "850, 950, 1000. Если игроку выпал численный "
                "сектор или x2, то ему предоставляется "
                "возможность угадать букву. Если игрок угадывает "
                "букву, то:\n1. при секторе x2 количество очков "
                "увеличивается ровно во столько, сколько было "
                "угаданных букв;\n"
                "2. при численном секторе количество очков "
                "увеличивается на выпавшее число.\n"
                "Если выпал сектор Б, то очки текущего игрока "
                "обнуляются, а ход переходит к следующему игроку.\n"
                "Если игрок назвал букву верно, то он получает "
                "возможность"
                " угадать слово целиком, или продолжить крутить "
                "барабан. В случае, когда буква названа неверно, "
                "ход передается другому игроку. Побеждает игрок, "
                "отгадавший все слово.\nВ игре доступны команды:\n"
                "/question - узнать вопрос в текущей игре\n"
                "/used - узнать, какие буквы уже назвали",
            )
        )

    async def _handle_play(self, message: UpdateMessage):
        game = await self.app.store.game.get_active_game_by_chat_id(
            message.chat_id
        )
        if game is None:
            await self.start_game_round(message)
        else:
            await self.app.store.telegram_api.send_message(
                Message(
                    chat_id=message.chat_id,
                    text="В этом чате уже идёт игра!",
                )
            )

    async def _handle_profile(self, message: UpdateMessage):
        user = await self.app.store.users.get_by_id(message.from_id)
        if not user:
            await self.app.store.users.create_user(
                message.from_id, message.username
            )
        user = await self.app.store.users.get_by_id(message.from_id)
        await self.app.store.telegram_api.send_message(
            Message(
                chat_id=message.chat_id,
                text=f"Профиль игрока @{user.username}:\n\n"
                f"Побед: {user.score}\n"
                f"Очков: {user.points}",
            )
        )

    async def _handle_question(self, message: UpdateMessage):
        game = await self.app.store.game.get_active_game_by_chat_id(
            message.chat_id
        )
        if game is not None:
            question = await self.app.store.game.get_question_by_id(
                game.question_id
            )
            await self.app.store.telegram_api.send_message(
                Message(
                    chat_id=message.chat_id,
                    text=f"Загадка: {question.text}",
                )
            )

    async def _handle_used(self, message: UpdateMessage):
        game = await self.app.store.game.get_active_game_by_chat_id(
            message.chat_id
        )
        if game is not None:
            letters = " ".join(
                list(self.game_state.used_letters(message.chat_id))
            )
            await self.app.store.telegram_api.send_message(
                Message(
                    chat_id=message.chat_id,
                    text=f"Использованные буквы: {letters}",
                )
            )

    async def _handle_stop(self, message: UpdateMessage):
        game = await self.app.store.game.get_active_game_by_chat_id(
            message.chat_id
        )
        if game is not None:
            players_and_users = self.game_state.players(message.chat_id)
            user_ids = [user.id for player, user in players_and_users]
            current_user = await self.app.store.users.get_by_id(message.from_id)
            if current_user.id in user_ids:
                await self.stop_game(message.chat_id)
            else:
                await self.app.store.telegram_api.send_message(
                    Message(
                        chat_id=message.chat_id,
                        text="Вы не участвуете в игре.",
                    )
                )
        else:
            await self.app.store.telegram_api.send_message(
                Message(
                    chat_id=message.chat_id,
                    text="В этом чате нет активных игр.",
                )
            )

    async def handle_callback_query(self, query: CallbackQuery) -> None:
        user = await self.app.store.users.get_by_id(query.from_id)
        if not user:
            await self.app.store.users.create_user(
                query.from_id, query.username
            )
        if query.data.startswith("participate"):
            game_id = int(query.data.split("_")[1])
            active_game = await self.app.store.game.get_active_game_by_chat_id(
                chat_id=query.chat_id
            )
            if (
                active_game
                and active_game.id == game_id
                and query.chat_id in self.registration_tasks
            ):
                await self.app.store.game.create_player(
                    user_id=query.from_id,
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
        elif query.data.startswith("spin"):
            current_player_id = self.game_state.current_player_idx(
                query.chat_id
            )
            current_user_id = self.game_state.players(query.chat_id)[
                current_player_id
            ][0].user_id
            if query.from_id == current_user_id:
                self.game_state.set_input_event(query.chat_id)
        elif query.data.startswith("guess"):
            current_player_id = self.game_state.current_player_idx(
                query.chat_id
            )
            current_user_id = self.game_state.players(query.chat_id)[
                current_player_id
            ][0].user_id
            if query.from_id == current_user_id:
                self.game_state.set_guessing_word(query.chat_id, True)
                self.game_state.set_input_event(query.chat_id)

    async def handle_game_input(self, message: UpdateMessage) -> None:
        chat_id = message.chat_id
        if not self.game_state.check(chat_id):
            return

        if not self.game_state.waiting_for_input(chat_id):
            return

        current_player, current_user = game_state["players"][
            game_state["current_player_idx"]
        ]
        if message.from_id != current_user.id:
            return

        guess = message.text.strip().upper()
        valid_input = False

        if len(guess) == 1 and not game_state["guessing_word"]:
            game_state["used_letters"].add(guess)
            if self.is_letter_revealed(
                game_state["word"], game_state["word_state"], guess
            ):
                match game_state["current_sector"]:
                    case 0:
                        await self.app.store.telegram_api.send_message(
                            Message(
                                chat_id=chat_id,
                                text="Эта буква уже была названа!"
                                " К сожалению, ваш счет не меняется."
                                " Ход переходит к следующему"
                                " игроку.",
                            )
                        )
                    case _:
                        await self.app.store.telegram_api.send_message(
                            Message(
                                chat_id=chat_id,
                                text="Эта буква уже была названа!"
                                " К сожалению, вы не получаете очков."
                                " Ход переходит к следующему"
                                " игроку.",
                            )
                        )
                await self.next_player(chat_id)
                self.input_events[chat_id].set()
                return

            new_word_state = self.reveal_letter(
                game_state["word"], game_state["word_state"], guess
            )
            if new_word_state != game_state["word_state"]:
                game_state["word_state"] = new_word_state
                guessed_letters = self.count_letter(game_state["word"], guess)
                points = 0
                match game_state["current_sector"]:
                    case 0:
                        game_state["scores"][current_player.user_id] *= (
                            guessed_letters + 1
                        )
                    case _:
                        points = (
                            guessed_letters
                            * self.SECTORS[game_state["current_sector"]]
                        )
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

                if self.is_game_over(chat_id):
                    await self.end_game(chat_id, current_user)
                    valid_input = True
                else:
                    reply_markup = {
                        "inline_keyboard": [
                            [
                                {
                                    "text": "Крутить барабан!",
                                    "callback_data": "spin",
                                },
                                {
                                    "text": "Угадать слово",
                                    "callback_data": "guess",
                                },
                            ]
                        ]
                    }
                    match game_state["current_sector"]:
                        case 0:
                            await self.app.store.telegram_api.send_message(
                                Message(
                                    chat_id=chat_id,
                                    text=f"Буква '{guess}' есть в слове! "
                                    f"Ваши очки "
                                    f"увеличиваются в {guessed_letters + 1} "
                                    f"раз(а).\nВы можете попробовать угадать "
                                    f"слово целиком, или "
                                    f"продолжить крутить барабан. "
                                    f"Слово: {masked_word}",
                                ),
                                reply_markup=json.dumps(reply_markup),
                            )
                        case _:
                            await self.app.store.telegram_api.send_message(
                                Message(
                                    chat_id=chat_id,
                                    text=f"Буква '{guess}' есть в слове! "
                                    f"+{points} "
                                    f"очков.  Вы можете попробовать угадать "
                                    f"слово целиком, или "
                                    f"продолжить крутить барабан.\n"
                                    f"Слово: {masked_word}",
                                ),
                                reply_markup=json.dumps(reply_markup),
                            )
            else:
                await self.app.store.telegram_api.send_message(
                    Message(
                        chat_id=chat_id, text=f"Буквы '{guess}' нет в слове!"
                    )
                )
                await self.next_player(chat_id)
                valid_input = True
        elif game_state["guessing_word"]:
            if guess == game_state["word"]:
                game_state["word_state"] = (1 << len(game_state["word"])) - 1
                await self.end_game(chat_id, current_user)
                valid_input = True
            else:
                await self.app.store.telegram_api.send_message(
                    Message(
                        chat_id=chat_id,
                        text="Неверное слово! "
                        "Ход переходит к "
                        "следующему игроку",
                    )
                )
                game_state["guessing_word"] = False
                await self.next_player(chat_id)
                valid_input = True
        else:
            await self.app.store.telegram_api.send_message(
                Message(
                    chat_id=chat_id,
                    text="Вы не можете называть слово целиком. "
                    "Назовите букву.",
                )
            )

        if valid_input and chat_id in self.input_events:
            self.input_events[chat_id].set()

    async def start_game_round(self, chat_id: int, game_id: int):
        game = await self.app.store.game.get_game_by_id(game_id)
        question = await self.app.store.game.get_question_by_id(
            game.question_id
        )
        players = await self.app.store.game.get_players_by_game_id(game_id)

        word = question.answer.upper()

        self.game_state.create_game_state(
            chat_id=chat_id,
            question=question.text,
            word=word,
            players=players,
            game_id=game_id,
        )

        game_task = asyncio.create_task(self.run_game(chat_id))
        self.game_tasks[chat_id] = game_task

    async def run_game(self, chat_id: int):
        try:
            masked_word = self.game_logic.get_masked_word(
                self.game_state.word(chat_id),
                self.game_state.word_state(chat_id),
            )
            await self.app.store.telegram_api.send_message(
                Message(
                    chat_id=chat_id,
                    text=f"Загадка: "
                    f"{self.game_state.question(chat_id)}\n"
                    f"Слово: {masked_word}\nДлина слова: "
                    f"{len(self.game_state.word(chat_id))} букв",
                )
            )

            while not self.game_logic.is_game_over(
                self.game_state.word(chat_id),
                self.game_state.word_state(chat_id),
            ):
                current_player, current_user = self.game_state.players(chat_id)[
                    self.game_state.current_player_idx(chat_id)
                ]

                if self.game_state.is_guessing_word(chat_id):
                    await self.app.store.telegram_api.send_message(
                        Message(
                            chat_id=chat_id,
                            text="Жду слово!",
                        ),
                        reply_markup=json.dumps({"force_reply": True}),
                    )
                else:
                    self.game_state.set_current_sector(
                        chat_id, self.game_logic.random_sector()
                    )
                    match self.game_state.current_sector(chat_id):
                        case 0:
                            await self.app.store.telegram_api.send_message(
                                Message(
                                    chat_id=chat_id,
                                    text=f"Ход игрока "
                                    f"@{current_user.username}.\n"
                                    f"Сектор x2 на барабане! "
                                    f"Назовите букву. ",
                                ),
                                reply_markup=json.dumps({"force_reply": True}),
                            )
                        case 1:
                            await self.app.store.telegram_api.send_message(
                                Message(
                                    chat_id=chat_id,
                                    text=f"Ход игрока "
                                    f"@{current_user.username}.\n"
                                    f"К сожалению, Вам выпал сектор Б. "
                                    f"Ваши очки обнуляются. "
                                    f"Ход переходит к другому игроку.",
                                ),
                                reply_markup=json.dumps({"force_reply": True}),
                            )
                            self.game_state.set_scores(
                                chat_id, current_player.user_id, 0
                            )
                            await self.next_player(chat_id)
                            continue
                        case 2:
                            await self.app.store.telegram_api.send_message(
                                Message(
                                    chat_id=chat_id,
                                    text=f"Ход игрока "
                                    f"@{current_user.username}.\n"
                                    f"К сожалению, Вам выпал сектор 0. "
                                    f"Ход переходит к другому игроку.",
                                ),
                                reply_markup=json.dumps({"force_reply": True}),
                            )
                            await self.next_player(chat_id)
                            continue
                        case _:
                            await self.app.store.telegram_api.send_message(
                                Message(
                                    chat_id=chat_id,
                                    text=f"Ход игрока "
                                    f"@{current_user.username}.\n"
                                    f"Сектор {self.SECTORS[
                                             game_state["current_sector"]
                                         ]} на барабане! Назовите букву.",
                                ),
                                reply_markup=json.dumps({"force_reply": True}),
                            )

                game_state["waiting_for_input"] = True

                try:
                    await asyncio.wait_for(
                        self.input_events[chat_id].wait(), timeout=30
                    )
                    self.input_events[chat_id].clear()
                except TimeoutError:
                    await self.app.store.telegram_api.send_message(
                        Message(
                            chat_id=chat_id,
                            text=f"@{current_user.username} "
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

    async def run_game(self, chat_id: int):
        # Existing game run logic
        pass

    async def next_player(self, chat_id: int):
        # Existing next player logic
        pass

    async def end_game(self, chat_id: int, winner=None):
        # Existing game end logic
        pass

    async def stop_game(self, chat_id: int):
        # Existing game stop logic
        pass


def create_bot_manager(app: "Application") -> BotManager:
    game_config = GameConfig()
    game_state = GameStateManager(game_config)
    game_logic = GameLogic(game_config)
    return BotManager(app, game_state, game_logic)
