import logging
import os
from typing import Any, Dict, List, Tuple

import requests
from dotenv import load_dotenv
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
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


# Анкета өрістері (CSV бағандарына сай)
OBJECT_FIELDS: List[Tuple[str, str]] = [
    ("object_id", "object_id (мысалы: 1)"),
    ("name_ru", "name_ru"),
    ("name_kk", "name_kk"),
    ("name_en", "name_en"),
    ("type", "type"),
    ("lat", "lat"),
    ("lon", "lon"),
    ("criticality", "criticality (High/Medium/Low)"),
    ("oblast_ru", "oblast_ru"),
    ("oblast_kk", "oblast_kk"),
    ("oblast_en", "oblast_en"),
    ("resource_type_ru", "resource_type_ru"),
    ("resource_type_kk", "resource_type_kk"),
    ("resource_type_en", "resource_type_en"),
    ("water_type_ru", "water_type_ru"),
    ("water_type_kk", "water_type_kk"),
    ("water_type_en", "water_type_en"),
    ("fauna_ru", "fauna_ru"),
    ("fauna_kk", "fauna_kk"),
    ("fauna_en", "fauna_en"),
    ("passport_date", "passport_date (YYYY-MM-DD)"),
    ("tech_state", "tech_state"),
    ("coords_center", "coords_center"),
    ("coords_north", "coords_north"),
    ("coords_south", "coords_south"),
    ("coords_east", "coords_east"),
    ("coords_west", "coords_west"),
]

DIAG_FIELDS: List[Tuple[str, str]] = [
    ("object_id", "object_id"),
    ("diag_id", "diag_id (толтырмасаңыз да болады)"),
    ("method", "method"),
    ("method_ru", "method_ru"),
    ("method_kk", "method_kk"),
    ("method_en", "method_en"),
    ("severity", "severity (High/Medium/Low)"),
    ("severity_ru", "severity_ru"),
    ("severity_kk", "severity_kk"),
    ("severity_en", "severity_en"),
    ("date", "date (YYYY-MM-DD немесе DD.MM.YYYY)"),
    ("description_ru", "description_ru"),
    ("description_kk", "description_kk"),
    ("description_en", "description_en"),
]


def menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("Объект анкета", callback_data="wizard_objects"),
                InlineKeyboardButton("Диагностика анкета", callback_data="wizard_diag"),
            ],
            [
                InlineKeyboardButton("Streamlit-ке өту", url="https://tiggrrr.streamlit.app"),
                InlineKeyboardButton("CSV түсініктеме", callback_data="csv_help"),
            ],
        ]
    )


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
        "Сәлем! Объект немесе диагностика анкетасын таңдаңыз — жауаптар Make-ке жіберіледі.\n"
        "CSV керек болса, анкетадан соң сілтеме шығады."
    )
    await update.message.reply_text(text, reply_markup=menu_keyboard())


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = (
        "Қалай қолдану:\n"
        "- /start басып, Объект немесе Диагностика анкетасын таңдаңыз.\n"
        "- Сұрақтарға кезекпен жауап беріңіз; соңында Make-ке жіберіледі.\n"
        "- CSV файл жіберсеңіз, файл мазмұны Make-ке өтеді.\n"
        f"Make webhook: {MAKE_WEBHOOK}"
    )
    await update.message.reply_text(text)


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.message.text:
        return
    # Анкета жүріп жатса, жауапты сол анкетаға жаза береміз
    pending = context.user_data.get("pending")
    if pending:
        await handle_answer(update, context)
        return

    content = update.message.text.strip()
    status = send_to_make({"type": "text", "text": content})
    await update.message.reply_text(f"Make-ке {status}\n\nАнкета үшін /start басыңыз.")


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


# ---------- Анкета ----------

async def on_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "csv_help":
        await query.edit_message_text(
            "CSV жүктеу үшін Streamlit ашыңыз: https://tiggrrr.streamlit.app\n"
            "Drag&Drop аймағына файлыңызды тастаңыз.",
            reply_markup=menu_keyboard(),
        )
        return

    if data in ("wizard_objects", "wizard_diag"):
        context.user_data["kind"] = "objects" if data == "wizard_objects" else "diagnostics"
        context.user_data["form"] = {}
        context.user_data["pending"] = OBJECT_FIELDS.copy() if data == "wizard_objects" else DIAG_FIELDS.copy()
        await ask_next_field(update, context)
        return

    await query.edit_message_text("Анкета бастау үшін /start басыңыз.", reply_markup=menu_keyboard())


async def ask_next_field(carrier: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    pending: List[Tuple[str, str]] = context.user_data.get("pending", [])
    if not pending:
        await finalize_form(carrier, context)
        return

    field_key, prompt = pending[0]
    context.user_data["current_field"] = field_key
    text = f"{prompt}\n(Жауап жазыңыз немесе /cancel)"

    if carrier.callback_query:
        await carrier.callback_query.edit_message_text(text)
    else:
        await carrier.message.reply_text(text)


async def handle_answer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message:
        return
    pending: List[Tuple[str, str]] = context.user_data.get("pending", [])
    if not pending:
        await update.message.reply_text("Алдымен /start басып, анкетаны таңдаңыз.")
        return

    field_key, _ = pending.pop(0)
    context.user_data["form"][field_key] = update.message.text.strip()
    context.user_data["pending"] = pending
    await ask_next_field(update, context)


async def finalize_form(carrier: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    kind = context.user_data.get("kind", "unknown")
    form = context.user_data.get("form", {})
    status = send_to_make({"type": "form", "kind": kind, "data": form})

    buttons = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("Streamlit-ке өту", url="https://tiggrrr.streamlit.app")],
            [InlineKeyboardButton("Басты меню", callback_data="menu")],
        ]
    )
    reply = f"Анкета Make-ке {status}.\nКелесі: Streamlit ашыңыз немесе жаңа анкетаны бастаңыз."

    if carrier.callback_query:
        await carrier.callback_query.edit_message_text(reply, reply_markup=buttons)
    else:
        await carrier.message.reply_text(reply, reply_markup=buttons)

    context.user_data.clear()


async def cmd_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data.clear()
    await update.message.reply_text("Анкета тоқтатылды. /start басып қайта бастаңыз.", reply_markup=menu_keyboard())


def main() -> None:
    load_dotenv()
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN not set. Add it to .env")

    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("cancel", cmd_cancel))
    app.add_handler(CallbackQueryHandler(on_button))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    logger.info("Bot is starting... Make webhook: %s", MAKE_WEBHOOK)
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
