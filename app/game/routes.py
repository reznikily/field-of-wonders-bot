import typing

from app.game.views import QuestionAddView, QuestionListView

if typing.TYPE_CHECKING:
    from app.web.app import Application


def setup_routes(app: "Application"):
    app.router.add_view("/game.add_question", QuestionAddView)
    app.router.add_view("/game.list_questions", QuestionListView)
