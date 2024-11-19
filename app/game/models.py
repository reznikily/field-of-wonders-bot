from enum import Enum

from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    String,
    func,
)
from sqlalchemy.dialects.postgresql import ENUM
from sqlalchemy.orm import relationship

from app.store.database.sqlalchemy_base import BaseModel


class GameState(Enum):
    ENDED = 0
    ACTIVE = 1


class PlayerModel(BaseModel):
    __tablename__ = "players"

    id = Column(BigInteger, primary_key=True, index=True)
    game_id = Column(BigInteger, ForeignKey("games.id", ondelete="CASCADE"))
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"))
    next_player_id = Column(BigInteger, ForeignKey("players.id"))
    in_game = Column(Boolean, default=True)
    active = Column(Boolean, default=True)
    points = Column(BigInteger, default=0)


class GameModel(BaseModel):
    __tablename__ = "games"

    id = Column(BigInteger, primary_key=True, index=True)
    question_id = Column(
        BigInteger, ForeignKey("questions.id", ondelete="CASCADE")
    )
    chat_id = Column(BigInteger, nullable=False)
    word_state = Column(BigInteger, default=0)
    game_state = Column(
        ENUM(GameState, name="gamestate"),
        nullable=False,
        default=GameState.ACTIVE,
    )
    winner_id = Column(BigInteger, ForeignKey("users.id"))
    players = relationship(PlayerModel, uselist=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    ended_at = Column(DateTime(timezone=True), default=None)


class QuestionModel(BaseModel):
    __tablename__ = "questions"

    id = Column(BigInteger, primary_key=True, index=True)
    text = Column(String)
    answer = Column(String)
    games = relationship(GameModel, uselist=True)
