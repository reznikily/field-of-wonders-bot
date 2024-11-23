import pytest
from unittest.mock import AsyncMock
from app.store.telegram_api.dataclasses import UpdateMessage, Message


@pytest.mark.asyncio
async def test_play_command(bot_manager):
    mock_message = UpdateMessage(
        id=1,
        chat_id=123,
        text="/play",
        from_id=1,
        username="test_user"
    )

    bot_manager.app.store.game.get_active_game_by_chat_id.side_effect = [None, AsyncMock(id=42)]
    bot_manager.app.store.game.create_game = AsyncMock()
    bot_manager.app.store.telegram_api.send_message = AsyncMock()

    await bot_manager.handle_command("/play", mock_message)

    bot_manager.app.store.game.create_game.assert_called_once_with(123)

    bot_manager.app.store.telegram_api.send_message.assert_called_once()
    sent_message = bot_manager.app.store.telegram_api.send_message.call_args[0][0]
    assert sent_message.chat_id == 123
    assert "Начинаем игру!" in sent_message.text
    assert "Даю 15 секунд на то, чтобы зарегистрироваться!" in sent_message.text

@pytest.mark.asyncio
async def test_start_command_new_user(bot_manager):
    mock_message = UpdateMessage(
        id=1,
        chat_id=123,
        text="/start",
        from_id=1,
        username="test_user"
    )
    bot_manager.app.store.users.get_by_id.return_value = None

    await bot_manager.handle_command("/start", mock_message)

    bot_manager.app.store.users.create_user.assert_called_once_with(1, "test_user")
    bot_manager.app.store.telegram_api.send_message.assert_called_once()
    sent_message = bot_manager.app.store.telegram_api.send_message.call_args[0][0]
    assert sent_message.chat_id == 123
    assert "@test_user, привет! Это игра Поле Чудес" in sent_message.text

@pytest.mark.asyncio
async def test_start_command_existing_user(bot_manager):
    mock_message = UpdateMessage(
        id=1,
        chat_id=123,
        text="/start",
        from_id=1,
        username="test_user"
    )
    user = AsyncMock()
    bot_manager.app.store.users.get_by_id.return_value = user

    await bot_manager.handle_command("/start", mock_message)

    bot_manager.app.store.users.create_user.assert_not_called()
    bot_manager.app.store.telegram_api.send_message.assert_called_once()
    sent_message = bot_manager.app.store.telegram_api.send_message.call_args[0][0]
    assert sent_message.chat_id == 123
    assert "Привет, @test_user! А я Вас уже знаю!" in sent_message.text

@pytest.mark.asyncio
async def test_rules_command(bot_manager):
    mock_message = UpdateMessage(
        id=1,
        chat_id=123,
        text="/rules",
        from_id=1,
        username="test_user"
    )

    await bot_manager.handle_command("/rules", mock_message)

    bot_manager.app.store.telegram_api.send_message.assert_called_once()
    sent_message = bot_manager.app.store.telegram_api.send_message.call_args[0][0]
    assert sent_message.chat_id == 123
    assert "Правила игры" in sent_message.text

@pytest.mark.asyncio
async def test_play_command_active_game(bot_manager):
    mock_message = UpdateMessage(
        id=1,
        chat_id=123,
        text="/play",
        from_id=1,
        username="test_user"
    )
    bot_manager.start_new_game = AsyncMock()
    bot_manager.app.store.game.get_active_game_by_chat_id.return_value = AsyncMock()

    await bot_manager.handle_command("/play", mock_message)

    bot_manager.start_new_game.assert_not_called()
    bot_manager.app.store.telegram_api.send_message.assert_called_once_with(
        Message(
            chat_id=123,
            text="В этом чате уже идёт игра!"
        )
    )

@pytest.mark.asyncio
async def test_profile_command_existing_user(bot_manager):
    mock_message = UpdateMessage(
        id=1,
        chat_id=123,
        text="/profile",
        from_id=3,
        username="existing_user"
    )
    user = AsyncMock(username="existing_user", score=5, points=150)
    bot_manager.app.store.users.get_by_id.return_value = user

    await bot_manager.handle_command("/profile", mock_message)

    bot_manager.app.store.users.create_user.assert_not_called()
    bot_manager.app.store.users.get_by_id.assert_called_with(3)
    bot_manager.app.store.telegram_api.send_message.assert_called_once()
    sent_message = bot_manager.app.store.telegram_api.send_message.call_args[0][0]
    assert sent_message.chat_id == 123
    assert "Профиль игрока @existing_user" in sent_message.text
    assert "Побед: 5" in sent_message.text
    assert "Очков: 150" in sent_message.text
