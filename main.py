import os
import logging
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

# ========== SETUP LOGGING ==========
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ========== LOAD ENV ==========
load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")

# Cek token & channel
if not TELEGRAM_BOT_TOKEN or not CHANNEL_ID:
    raise SystemExit("❌ TELEGRAM_BOT_TOKEN atau CHANNEL_ID belum diset di .env / Railway!")

# ========== HANDLERS ==========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🔥 Blast ke Channel", callback_data="blast")],
        [InlineKeyboardButton("ℹ️ Info", callback_data="info")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Pilih menu:", reply_markup=reply_markup)


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "blast":
        try:
            await context.bot.send_message(
                chat_id=CHANNEL_ID,
                text="🚀 Ini pesan blast otomatis dari bot!"
            )
            await query.edit_message_text("✅ Pesan berhasil dikirim ke channel.")
        except Exception as e:
            logger.error(f"❌ Error mengirim ke channel: {e}")
            await query.edit_message_text(f"❌ Gagal blast: {e}")

    elif query.data == "info":
        await query.edit_message_text("🤖 Bot aktif dan siap jalan!")

# ========== MAIN ==========
def main():
    print("✅ Bot jalan dengan:")
    print("🔑 TELEGRAM_BOT_TOKEN:", TELEGRAM_BOT_TOKEN[:10] + "...")
    print("📢 CHANNEL_ID:", CHANNEL_ID)

    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))

    app.run_polling()

if __name__ == "__main__":
    main()
