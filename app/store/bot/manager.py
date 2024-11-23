import asyncio
import json
import random
import traceback
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

        self.SECTORS = [
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
        match command:
            case "/start":
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
            case "/rules":
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
            case "/play":
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
            case "/profile":
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
            case "/question":
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
            case "/used":
                game = await self.app.store.game.get_active_game_by_chat_id(
                    message.chat_id
                )
                if game is not None:
                    letters = " ".join(
                        list(self.game_states[message.chat_id]["used_letters"])
                    )
                    await self.app.store.telegram_api.send_message(
                        Message(
                            chat_id=message.chat_id,
                            text=f"Использованные буквы: {letters}",
                        )
                    )
            case "/stop":
                game = await self.app.store.game.get_active_game_by_chat_id(
                    message.chat_id
                )
                if game is not None:
                    players_and_users = self.game_states[message.chat_id]["players"]
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
            case _:
                await self.app.store.telegram_api.send_message(
                    Message(
                        chat_id=message.chat_id,
                        text="Простите, но таких команд не знаю :(",
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
            current_player_id = self.game_states[query.chat_id][
                "current_player_idx"
            ]
            current_user_id = self.game_states[query.chat_id]["players"][
                current_player_id
            ][0].user_id
            if query.from_id == current_user_id:
                self.input_events[query.chat_id].set()
        elif query.data.startswith("guess"):
            current_player_id = self.game_states[query.chat_id][
                "current_player_idx"
            ]
            current_user_id = self.game_states[query.chat_id]["players"][
                current_player_id
            ][0].user_id
            if query.from_id == current_user_id:
                self.game_states[query.chat_id]["guessing_word"] = True
                self.input_events[query.chat_id].set()

    async def start_new_game(self, message: UpdateMessage):
        await self.app.store.game.create_game(message.chat_id)
        game = await self.app.store.game.get_active_game_by_chat_id(
            message.chat_id
        )
        if game is None:
            raise Exception("No active game in the chat.")
            return
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
            "question": question.text,
            "word": word,
            "word_state": 0,
            "current_player_idx": 0,
            "current_sector": -1,
            "guessing_word": False,
            "used_letters": set(),
            "players": players,
            "scores": {
                player.user_id: player.points for player, user in players
            },
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
                    text=f"Загадка: {game_state["question"]}\n"
                    f"Слово: {masked_word}\nДлина слова: "
                    f"{len(game_state['word'])} букв",
                )
            )

            while not self.is_game_over(chat_id):
                current_player, current_user = game_state["players"][
                    game_state["current_player_idx"]
                ]

                if game_state["guessing_word"]:
                    await self.app.store.telegram_api.send_message(
                        Message(
                            chat_id=chat_id,
                            text="Жду слово!",
                        ),
                        reply_markup=json.dumps({"force_reply": True}),
                    )
                else:
                    game_state["current_sector"] = random.randint(
                        0, len(self.SECTORS) - 1
                    )
                    match game_state["current_sector"]:
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
                            game_state["scores"][current_player.user_id] = 0
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

    async def handle_game_input(self, message: UpdateMessage) -> None:
        chat_id = message.chat_id
        if chat_id not in self.game_states:
            return

        game_state = self.game_states[chat_id]
        if not game_state["waiting_for_input"]:
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

    async def next_player(self, chat_id: int):
        game_state = self.game_states[chat_id]
        current_player, current_user = game_state["players"][
            game_state["current_player_idx"]
        ]
        del current_user

        next_idx = (game_state["current_player_idx"] + 1) % len(
            game_state["players"]
        )
        next_player, next_user = game_state["players"][next_idx]
        del next_user

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

            for player, user in game_state["players"]:
                await self.app.store.game.update_user_points_and_score(
                    user.id,
                    game_state["scores"][user.id] + user.points,
                    user.score + 1,
                )
                await self.app.store.game.update_player_status(
                    player.id, in_game=False
                )

            scores_text = "Финальный счёт:\n" + "\n".join(
                f"@{user.username}: " f"{game_state['scores'][user.id]} очков"
                for player, user in game_state["players"]
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
                    winner_id=winner.id,
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

        except Exception:
            self.logger.error("Error ending game.")
            self.logger.error(traceback.format_exc())
            await self.app.store.telegram_api.send_message(
                Message(
                    chat_id=chat_id,
                    text="Произошла ошибка при завершении игры.",
                )
            )

    async def stop_game(self, chat_id: int):
        try:
            game = await self.app.store.game.get_active_game_by_chat_id(chat_id)
            await self.app.store.game.end_game(
                game_id=game.id,
                winner_id=None,
                word_state=game.word_state,
            )

            game_state = self.game_states[chat_id]

            for player, user in game_state["players"]:
                await self.app.store.game.update_user_points_and_score(
                    user.id,
                    game_state["scores"][user.id] + user.points,
                    user.score + 1,
                )
                await self.app.store.game.update_player_status(
                    player.id, in_game=False
                )

            scores_text = "Финальный счёт:\n" + "\n".join(
                f"@{user.username}: " f"{game_state['scores'][user.id]} очков"
                for player, user in game_state["players"]
            )

            await self.app.store.telegram_api.send_message(
                Message(
                    chat_id=chat_id,
                    text=f"Завершаю игру.\n\n"
                    f"{scores_text}",
                )
            )

            if chat_id in self.game_tasks:
                self.game_tasks[chat_id].cancel()
                del self.game_tasks[chat_id]

        except Exception:
            self.logger.error("Error ending game.")
            self.logger.error(traceback.format_exc())
            await self.app.store.telegram_api.send_message(
                Message(
                    chat_id=chat_id,
                    text="Произошла ошибка при завершении игры.",
                )
            )
