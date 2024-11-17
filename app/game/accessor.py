import random
import typing

from sqlalchemy import func, insert, select, update

from app.base.base_accessor import BaseAccessor
from app.game.models import GameModel, PlayerModel, QuestionModel

if typing.TYPE_CHECKING:
    from app.web.app import Application


class GameAccessor(BaseAccessor):
    def __init__(self, app: "Application", *args, **kwargs) -> None:
        super().__init__(app, *args, **kwargs)

    async def connect(self, app: "Application") -> None:
        self.app = app

    async def question_count(self) -> int:
        request = select(QuestionModel)
        async with self.app.database.session as session:
            res = await session.execute(request)

            return len(res.all())

    async def create_game(self, chat_id: int) -> None:
        question_count = await self.question_count()
        question_id = random.randint(1, question_count)

        request = insert(GameModel).values(
            chat_id=chat_id, question_id=question_id
        )
        async with self.app.database.session as session:
            await session.execute(request)
            await session.commit()

    async def get_active_game_by_chat_id(
        self, chat_id: int
    ) -> GameModel | None:
        request = select(GameModel).where(GameModel.game_state == 1)
        async with self.app.database.session as session:
            res = await session.execute(request)

            for game in res:
                if game[0].chat_id == chat_id:
                    return game[0]

        return None

    async def get_game_by_id(self, game_id: int) -> GameModel | None:
        request = select(GameModel)
        async with self.app.database.session as session:
            res = await session.execute(request)

            for game in res:
                if game[0].id == game_id:
                    return game[0]

        return None

    async def get_question_by_id(
        self, question_id: int
    ) -> QuestionModel | None:
        request = select(QuestionModel)
        async with self.app.database.session as session:
            res = await session.execute(request)

            for question in res:
                if question[0].id == question_id:
                    return question[0]

        return None

    async def create_player(
        self, user_id: int, username: str, game_id: int
    ) -> None:
        request = insert(PlayerModel).values(
            user_id=user_id, username=username, game_id=game_id
        )
        async with self.app.database.session as session:
            await session.execute(request)
            await session.commit()

    async def get_player(
        self, user_id: int, game_id: int
    ) -> PlayerModel | None:
        request = select(PlayerModel)
        async with self.app.database.session as session:
            res = await session.execute(request)

            for player in res:
                if (
                    player[0].user_id == user_id
                    and player[0].game_id == game_id
                ):
                    return player[0]

        return None

    async def get_players_by_game_id(self, game_id: int):
        request = select(PlayerModel)
        async with self.app.database.session as session:
            res = await session.execute(request)

            return [player[0] for player in res if player[0].game_id == game_id]

    async def update_word_state(self, game_id: int, word_state: int) -> None:
        async with self.app.database.session as session:
            await session.execute(
                update(GameModel)
                .where(GameModel.id == game_id)
                .values(word_state=word_state)
            )
            await session.commit()

    async def update_next_player(
        self, player_id: int, next_player_id: int
    ) -> None:
        async with self.app.database.session as session:
            await session.execute(
                update(PlayerModel)
                .where(PlayerModel.id == player_id)
                .values(next_player_id=next_player_id)
            )
            await session.commit()

    async def update_player_points(self, player_id: int, points: int) -> None:
        async with self.app.database.session as session:
            await session.execute(
                update(PlayerModel)
                .where(PlayerModel.id == player_id)
                .values(points=points)
            )
            await session.commit()

    async def update_player_status(self, player_id: int, in_game: bool) -> None:
        async with self.app.database.session as session:
            await session.execute(
                update(PlayerModel)
                .where(PlayerModel.id == player_id)
                .values(in_game=in_game)
            )
            await session.commit()

    async def end_game(
        self, game_id: int, winner_id: int | None = None, word_state: int = 0
    ) -> None:
        async with self.app.database.session as session:
            await session.execute(
                update(GameModel)
                .where(GameModel.id == game_id)
                .values(
                    game_state=0,
                    winner_id=winner_id,
                    word_state=word_state,
                    ended_at=func.now(),
                )
            )
            await session.commit()
