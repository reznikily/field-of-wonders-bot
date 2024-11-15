import typing

from app.base.base_accessor import BaseAccessor

if typing.TYPE_CHECKING:
    from app.web.app import Application


class UserAccessor(BaseAccessor):
    def __init__(self, app: "Application", *args, **kwargs) -> None:
        super().__init__(app, *args, **kwargs)
