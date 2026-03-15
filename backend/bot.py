import os
import logging
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")
APP_URL = os.getenv("APP_URL", "https://placeholder.trycloudflare.com")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(
            text="🎮 Играть",
            web_app=WebAppInfo(url=APP_URL)
        )]
    ])
    await update.message.reply_text(
        "👋 Привет! Нажми кнопку чтобы открыть игру.",
        reply_markup=keyboard
    )


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"✅ Сервер работает\n🔗 URL: {APP_URL}")


def run_bot():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("status", status))
    logger.info("Bot started. Polling...")
    app.run_polling()


if __name__ == "__main__":
    run_bot()
