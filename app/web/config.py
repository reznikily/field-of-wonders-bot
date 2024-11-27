import typing
from dataclasses import dataclass

import yaml

if typing.TYPE_CHECKING:
    from app.web.app import Application


@dataclass
class BotConfig:
    token: str


@dataclass
class DatabaseConfig:
    host: str
    port: int
    user: str
    password: str
    name: str


@dataclass
class SessionConfig:
    key: str


@dataclass
class AdminConfig:
    login: str
    password: str


@dataclass
class Config:
    admin: AdminConfig | None = None
    bot: BotConfig | None = None
    database: DatabaseConfig | None = None
    session: SessionConfig | None = None


def setup_config(app: "Application", config_path: str):
    with open(config_path, "r") as f:
        raw_config = yaml.safe_load(f)

    app.config = Config(
        session=SessionConfig(
            key=raw_config["store"]["session"]["key"],
        ),
        admin=AdminConfig(
            login=raw_config["store"]["admin"]["login"],
            password=raw_config["store"]["admin"]["password"],
        ),
        bot=BotConfig(
            token=raw_config["store"]["telegram"]["token"],
        ),
        database=DatabaseConfig(**raw_config["database"]),
    )
