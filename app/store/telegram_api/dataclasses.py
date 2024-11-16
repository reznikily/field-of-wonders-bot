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
class UpdateObject:
    id: int
    message: UpdateMessage
