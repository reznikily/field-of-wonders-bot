from sqlalchemy import CHAR, BigInteger, Column

from app.store.database.sqlalchemy_base import BaseModel


class AdminModel(BaseModel):
    __tablename__ = "admins"
    id = Column(BigInteger, primary_key=True)
    login = Column(CHAR(20), unique=True, nullable=False)
    password = Column(CHAR(20), nullable=False)
