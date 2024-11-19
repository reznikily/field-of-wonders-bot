from dataclasses import dataclass


@dataclass
class Message:
    chat_id: int
    text: str


@dataclass
class UpdateMessage:
    id: int
    chat_id: int
    from_id: int
    username: str
    text: str


@dataclass
class CallbackQuery:
    id: int
    chat_id: int
    from_id: int
    username: str
    data: str


@dataclass
class CallbackAnswer:
    callback_id: int
    text: str


@dataclass
class UpdateObject:
    id: int
    type: str
    object: UpdateMessage | CallbackQuery
