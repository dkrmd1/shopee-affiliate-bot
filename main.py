import logging
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# Konfigurasi logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# Konfigurasi bot
TELEGRAM_BOT_TOKEN = "ISI_TOKEN_MU"
ADMIN_ID = 1239490619
CHANNEL_ID = "@promoshopee22a"
CHANNEL_USERNAME = "@promoshopee22a"


# Command /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Halo, bot Shopee Affiliate sudah aktif!")


# Handler pesan teks
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text
    await update.message.reply_text(f"Pesan kamu: {user_message}")


# ✅ Tambahan perbaikan: handler foto (biar gak error)
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    photo = update.message.photo[-1]  # ambil ukuran terbesar
    file_id = photo.file_id
    await update.message.reply_text(f"📸 Foto diterima!\nFile ID: {file_id}")


# Main function
def main():
    logger.info("🚀 Starting Shopee Affiliate Bot...")

    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Handler command
    application.add_handler(CommandHandler("start", start))

    # Handler pesan teks
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Handler foto
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))

    logger.info("✅ Telegram application built successfully")

    # Jalankan bot
    application.run_polling()


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.error(f"💥 Critical error starting bot: {e}", exc_info=True)
