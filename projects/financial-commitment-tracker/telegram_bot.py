"""Telegram notification sender."""

import os
import logging

import httpx

logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")


def send_telegram_message(text: str) -> bool:
    """Send a message via Telegram bot. Returns True on success."""
    if not BOT_TOKEN or not CHAT_ID:
        logger.warning("Telegram not configured — skipping notification: %s", text[:80])
        return False

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    try:
        resp = httpx.post(
            url,
            json={
                "chat_id": CHAT_ID,
                "text": text,
                "parse_mode": "Markdown",
            },
            timeout=10,
        )
        if resp.status_code == 200:
            return True
        logger.error("Telegram API error %d: %s", resp.status_code, resp.text)
        return False
    except httpx.HTTPError as e:
        logger.error("Telegram send failed: %s", e)
        return False
