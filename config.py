from dataclasses import dataclass
from typing import Any

from environs import Env
from google.oauth2.service_account import Credentials


SCOPES = [
    "https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.file", "https://www.googleapis.com/auth/drive"
]


@dataclass
class DbConfig:
    host: str
    password: str
    user: str
    database: str


@dataclass
class TgBot:
    token: str
    admin_ids: int


@dataclass
class Miscellaneous:
    scoped_credentials: Any = None


@dataclass
class Config:
    tg_bot: TgBot
    db: DbConfig
    misc: Miscellaneous


def get_scoped_credentials(scopes):
    google_credentials = Credentials.from_service_account_file("tgbot/creds.json")

    def prepare_credentials():
        return google_credentials.with_scopes(scopes)

    return prepare_credentials


def load_config(path: str = None):
    env = Env()
    env.read_env(path)
    scoped_credentials = get_scoped_credentials(SCOPES)

    return Config(
        tg_bot=TgBot(
            token=env.str("BOT_TOKEN"),
            admin_ids=env.list("ADMINS"),
        ),
        db=DbConfig(
            host=env.str("DB_HOST"),
            password=env.str("DB_PASS"),
            user=env.str("DB_USER"),
            database=env.str("DB_NAME")
        ),
        misc=Miscellaneous(
            scoped_credentials
        )
    )
