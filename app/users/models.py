from sqlalchemy import BigInteger, Column, String
from sqlalchemy.orm import relationship

from app.game.models import GameModel, PlayerModel
from app.store.database.sqlalchemy_base import BaseModel


class UserModel(BaseModel):
    __tablename__ = "users"

    id = Column(BigInteger, primary_key=True, index=True)
    username = Column(String, unique=True, nullable=False)
    role = Column(String, nullable=False)
    score = Column(BigInteger, default=0)
    points = Column(BigInteger, default=0)
    player_profiles = relationship(PlayerModel, uselist=True)
    wins = relationship(GameModel, uselist=True)