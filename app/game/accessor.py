import random
import typing

from sqlalchemy import insert, select

from app.base.base_accessor import BaseAccessor
from app.game.models import GameModel, QuestionModel

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
