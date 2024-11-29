from aiohttp.web_exceptions import HTTPBadRequest
from aiohttp_apispec import request_schema, response_schema

from app.game.schemes import (
    ListQuestionSchema,
    QuestionSchema,
)
from app.web.app import View
from app.web.mixins import AuthRequiredMixin
from app.web.utils import json_response


class QuestionAddView(AuthRequiredMixin, View):
    @request_schema(QuestionSchema)
    @response_schema(QuestionSchema, 200)
    async def post(self):
        data = await self.request.json()
        text = data["text"]
        answer = data["answer"]

        if len(answer) < 2:
            raise HTTPBadRequest

        question = await self.store.game.create_question(
            text=text, answer=answer
        )
        return json_response(data=QuestionSchema().dump(question))


class QuestionListView(AuthRequiredMixin, View):
    @response_schema(ListQuestionSchema, 200)
    async def get(self):
        questions = await self.request.app.store.game.list_questions()
        if not questions:
            return json_response(data={"questions": questions})

        raw_questions = [
            QuestionSchema().dump(question[0]) for question in questions
        ]
        return json_response(data={"questions": raw_questions})
