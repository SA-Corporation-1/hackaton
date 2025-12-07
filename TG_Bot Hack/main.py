import logging
import os
from typing import Any, Dict

import requests
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

# --- Config ---
MAKE_WEBHOOK = os.getenv(
    "MAKE_WEBHOOK_URL",
    "https://hook.eu2.make.com/rmxwms8d9mauollpe776ntpd4ucgnkzp",
)

# --- Logging ---
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)


def send_to_make(payload: Dict[str, Any]) -> str:
    """Send payload to Make webhook; return status string."""
    try:
        resp = requests.post(MAKE_WEBHOOK, json=payload, timeout=10)
        if resp.ok:
            return "жіберілді"
        return f"қате {resp.status_code}"
    except Exception as e:
        logger.warning("Make webhook error: %s", e)
        return f"қате: {e}"


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = (
        "Сәлем! Бұл бот барлық хабарламаны Make вебхугіне жібереді.\n"
        "Жай мәтін жазыңыз немесе CSV файлын жіберіңіз."
    )
    await update.message.reply_text(text)


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = (
        "Қалай қолдану:\n"
        "1) Мәтін жазыңыз — Make-ке JSON ретінде жіберіледі.\n"
        "2) CSV файл жіберіңіз — файл мазмұны толық Make-ке жіберіледі.\n"
        f"Webhook: {MAKE_WEBHOOK}"
    )
    await update.message.reply_text(text)


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.message.text:
        return
    content = update.message.text.strip()
    status = send_to_make({"type": "text", "text": content})
    await update.message.reply_text(f"Make-ке {status}")


async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.message.document:
        return
    doc = update.message.document
    if not doc.file_name.lower().endswith(".csv"):
        await update.message.reply_text("Тек CSV файл қабылдаймын.")
        return

    file = await doc.get_file()
    content_bytes = await file.download_as_bytearray()
    try:
        content_text = content_bytes.decode("utf-8")
    except Exception:
        content_text = content_bytes.decode("latin-1", errors="replace")

    payload = {
        "type": "csv",
        "file_name": doc.file_name,
        "content": content_text,
    }
    status = send_to_make(payload)
    await update.message.reply_text(f"CSV Make-ке {status}")


def main() -> None:
    load_dotenv()
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN not set. Add it to .env")

    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    logger.info("Bot is starting... Make webhook: %s", MAKE_WEBHOOK)
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
