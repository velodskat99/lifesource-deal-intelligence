from unittest.mock import AsyncMock, patch


async def test_send_message_calls_api():
    from lifesource.notifications.telegram import send_telegram_message

    with patch("lifesource.notifications.telegram.Bot") as MockBot:
        mock_bot = MockBot.return_value
        mock_bot.send_message = AsyncMock()

        await send_telegram_message("Hello!", token="test-token", chat_id="123")

        mock_bot.send_message.assert_called_once_with(chat_id="123", text="Hello!")


async def test_send_message_splits_long_messages():
    from lifesource.notifications.telegram import send_telegram_message

    long_msg = "x" * 5000  # Telegram limit is 4096
    with patch("lifesource.notifications.telegram.Bot") as MockBot:
        mock_bot = MockBot.return_value
        mock_bot.send_message = AsyncMock()

        await send_telegram_message(long_msg, token="test-token", chat_id="123")

        assert mock_bot.send_message.call_count == 2
