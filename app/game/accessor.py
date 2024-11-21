import random

from sqlalchemy import func, insert, select, update

from app.base.base_accessor import BaseAccessor
from app.game.models import GameModel, GameState, PlayerModel, QuestionModel
from app.users.models import UserModel


class GameAccessor(BaseAccessor):
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
        request = select(GameModel).where(
            GameModel.game_state == GameState.ACTIVE
            and GameModel.chat_id == chat_id
        )
        async with self.app.database.session as session:
            res = await session.execute(request)
            row = res.first()
            if row is not None:
                return row[0]

        return None

    async def get_game_by_id(self, game_id: int) -> GameModel | None:
        request = select(GameModel).where(GameModel.id == game_id)
        async with self.app.database.session as session:
            res = await session.execute(request)
            row = res.first()
            if row is not None:
                return row[0]

        return None

    async def create_question(self, text: str, answer: str) -> None:
        request = insert(QuestionModel).values(text=text, answer=answer)
        async with self.app.database.session as session:
            await session.execute(request)
            await session.commit()

    async def get_question_by_id(
        self, question_id: int
    ) -> QuestionModel | None:
        request = select(QuestionModel).where(QuestionModel.id == question_id)
        async with self.app.database.session as session:
            res = await session.execute(request)
            row = res.first()
            if row is not None:
                return row[0]

        return None

    async def list_questions(self):
        request = select(QuestionModel)
        async with self.app.database.session as session:
            res = await session.execute(request)
            return res.all()

    async def create_player(self, user_id: int, game_id: int) -> None:
        request = insert(PlayerModel).values(user_id=user_id, game_id=game_id)
        async with self.app.database.session as session:
            await session.execute(request)
            await session.commit()

    async def get_players_by_game_id(self, game_id: int):
        request = (
            select(PlayerModel, UserModel)
            .join(UserModel, PlayerModel.user_id == UserModel.id)
            .where(PlayerModel.game_id == game_id)
        )
        async with self.app.database.session as session:
            res = await session.execute(request)

            return [
                [player, user]
                for player, user in res.all()
                if player.game_id == game_id
            ]

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

    async def update_user_points_and_score(self, user_id: int, points: int, score: int) -> None:
        async with self.app.database.session as session:
            await session.execute(
                update(UserModel)
                .where(UserModel.id == user_id)
                .values(points=points, score=score)
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
                    game_state=GameState.ENDED,
                    winner_id=winner_id,
                    word_state=word_state,
                    ended_at=func.now(),
                )
            )
            await session.commit()
