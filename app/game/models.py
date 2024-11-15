from sqlalchemy import (
    BigInteger,
    Column,
    DateTime,
    ForeignKey,
    LargeBinary,
    String,
)
from sqlalchemy.orm import relationship

from app.store.database.sqlalchemy_base import BaseModel


class PlayerModel(BaseModel):
    __tablename__ = "players"

    id = Column(BigInteger, primary_key=True, index=True)
    game_id = Column(BigInteger, ForeignKey("games.id", ondelete="CASCADE"))
    user_id = Column(BigInteger, ForeignKey("users.id"))
    next_player_id = Column(BigInteger, ForeignKey("players.id"))
    points = Column(BigInteger, default=0)


class GameModel(BaseModel):
    __tablename__ = "games"

    id = Column(BigInteger, primary_key=True, index=True)
    question_id = Column(
        BigInteger, ForeignKey("questions.id", ondelete="CASCADE")
    )
    chat_id = Column(BigInteger, nullable=False)
    word_state = Column(LargeBinary, default=0)
    game_state = Column(BigInteger, default=0)
    current_player_id = Column(BigInteger, ForeignKey("players.id"))
    winner_id = Column(BigInteger, ForeignKey("users.id"))
    players = relationship(PlayerModel, uselist=True)
    created_at = Column(DateTime)
    ended_at = Column(DateTime)


class QuestionModel(BaseModel):
    __tablename__ = "questions"

    id = Column(BigInteger, primary_key=True, index=True)
    text = Column(String)
    answer = Column(String)
    games = relationship(GameModel, uselist=True)
