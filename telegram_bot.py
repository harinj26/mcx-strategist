"""
MCX Natural Gas Strategist — Telegram Bot.

Commands:
  /morning   — run live analysis and stream the briefing
  /start     — welcome message
  /help      — list commands

Setup:
  1. Create a bot via @BotFather and get your TELEGRAM_BOT_TOKEN.
  2. Get your TELEGRAM_CHAT_ID (send a message, then check
     https://api.telegram.org/bot<TOKEN>/getUpdates).
  3. Set both in your .env file.
  4. Run: python telegram_bot.py
"""

from __future__ import annotations

import logging
import os
import textwrap

from dotenv import load_dotenv
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import Application, CommandHandler, ContextTypes

from strategist import get_full_analysis

load_dotenv()

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

_TELEGRAM_MAX = 4096


def _split_message(text: str, max_len: int = _TELEGRAM_MAX) -> list[str]:
    return textwrap.wrap(text, width=max_len, replace_whitespace=False,
                         break_long_words=False, break_on_hyphens=False)


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Welcome to the *MCX Natural Gas Strategist* bot.\n\n"
        "Commands:\n"
        "  /morning — run the full morning analysis\n"
        "  /help    — show this message",
        parse_mode=ParseMode.MARKDOWN,
    )


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await cmd_start(update, context)


async def cmd_morning(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = await update.message.reply_text(
        "Fetching live data and running analysis… this may take 30-60 seconds."
    )

    try:
        analysis = await get_full_analysis()
    except Exception as exc:
        logger.exception("Analysis failed")
        await msg.edit_text(f"Analysis failed: {exc}")
        return

    if not analysis.strip():
        await msg.edit_text("No analysis returned. Check your ANTHROPIC_API_KEY.")
        return

    await msg.delete()

    chunks = _split_message(analysis)
    for i, chunk in enumerate(chunks):
        await update.message.reply_text(chunk, parse_mode=None)
        if i == 0 and len(chunks) > 1:
            logger.info("Sending %d message chunks", len(chunks))


def main() -> None:
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        raise SystemExit(
            "TELEGRAM_BOT_TOKEN is not set. "
            "Add it to your .env file or environment."
        )

    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("start",   cmd_start))
    app.add_handler(CommandHandler("help",    cmd_help))
    app.add_handler(CommandHandler("morning", cmd_morning))

    logger.info("Bot is running. Send /morning in Telegram.")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
