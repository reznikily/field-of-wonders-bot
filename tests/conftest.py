import pytest
from unittest.mock import AsyncMock

@pytest.fixture
def mock_app():
    from app.web.app import Application
    app = AsyncMock(spec=Application)
    app.store.users.get_by_id = AsyncMock()
    app.store.users.create_user = AsyncMock()
    app.store.telegram_api.send_message = AsyncMock()
    app.store.game.get_active_game_by_chat_id = AsyncMock()
    app.store.game.create_game = AsyncMock()
    app.store.game.get_question_by_id = AsyncMock()
    app.store.game.get_players_by_game_id = AsyncMock()
    app.store.game.update_word_state = AsyncMock()
    app.store.game.update_player_points = AsyncMock()
    app.store.game.update_next_player = AsyncMock()
    app.store.game.end_game = AsyncMock()
    return app

@pytest.fixture
def bot_manager(mock_app):
    from app.store.bot.manager import BotManager
    return BotManager(mock_app)
