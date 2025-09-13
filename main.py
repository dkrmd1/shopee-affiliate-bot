import os
import logging
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler
from apscheduler.schedulers.background import BackgroundScheduler

# Logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# Ambil variabel dari Railway Variables
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
CHANNEL_ID = os.environ.get("CHANNEL_ID")  # contoh: "@promoshopee22a"

# === Command Start ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📢 Promo Terbaru", callback_data="promo")],
        [InlineKeyboardButton("ℹ️ Tentang Bot", callback_data="about")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "Halo 👋\nSelamat datang di Bot Promo Shopee!\n\nPilih menu di bawah:",
        reply_markup=reply_markup,
    )

# === Callback Button ===
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "promo":
        await query.edit_message_text("🔥 Promo terbaru ada di channel kami: https://t.me/promoshopee22a")
    elif query.data == "about":
        await query.edit_message_text("🤖 Bot ini otomatis mengirim promo ke channel Shopee!")

# === Blast ke Channel ===
def blast_message():
    try:
        text = "🚀 Promo baru tersedia! Cek sekarang di https://shopee.co.id"
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        res = requests.post(url, data={"chat_id": CHANNEL_ID, "text": text})
        if res.status_code == 200:
            logger.info("✅ Blast terkirim ke channel")
        else:
            logger.error(f"❌ Gagal kirim blast: {res.text}")
    except Exception as e:
        logger.error(f"❌ Error blast: {e}")

def main():
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))

    # Scheduler untuk blast otomatis
    scheduler = BackgroundScheduler()
    scheduler.add_job(blast_message, "interval", hours=1)  # setiap 1 jam
    scheduler.start()

    logger.info("🤖 Bot berjalan...")
    app.run_polling()

if __name__ == "__main__":
    main()
