import logging

from telegram import Bot

logger = logging.getLogger(__name__)

TELEGRAM_MAX_LENGTH = 4096


async def send_telegram_message(text: str, token: str, chat_id: str) -> None:
    """Send a message via Telegram Bot API. Splits long messages."""
    bot = Bot(token=token)

    chunks = []
    while len(text) > TELEGRAM_MAX_LENGTH:
        split_at = text.rfind("\n", 0, TELEGRAM_MAX_LENGTH)
        if split_at == -1:
            split_at = TELEGRAM_MAX_LENGTH
        chunks.append(text[:split_at])
        text = text[split_at:].lstrip("\n")
    if text:
        chunks.append(text)

    for chunk in chunks:
        await bot.send_message(chat_id=chat_id, text=chunk)
        logger.info(f"Sent Telegram message ({len(chunk)} chars)")
