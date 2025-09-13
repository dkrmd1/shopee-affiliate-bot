import logging
import asyncio
from telegram import Update, BotCommand
from telegram.ext import Application, CommandHandler, ContextTypes

# Token bot
TELEGRAM_BOT_TOKEN = "ISI_TOKEN_BOT_KAMU"

# Username channel publik (pakai @)
CHANNEL_USERNAME = "@promoshopee22a"

# Konfigurasi logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)


# --- Command Handlers ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Halo! Gunakan menu di bawah untuk memilih fitur.")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("ℹ️ Menu Bantuan:\n/start - Mulai bot\n/help - Bantuan\n/blast - Kirim pesan ke channel")


async def blast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        pesan = "🔥 Promo terbaru! Cek di sini 👉 https://t.me/promoshopee22a"

        await context.bot.send_message(
            chat_id=CHANNEL_USERNAME,
            text=pesan,
            disable_web_page_preview=True  # cegah error preview
        )

        await update.message.reply_text("✅ Pesan berhasil dikirim ke channel.")
    except Exception as e:
        logger.error(f"❌ Error mengirim ke channel: {e}")
        await update.message.reply_text(f"Gagal kirim pesan ke channel: {e}")


# --- Main Function ---
async def main():
    # Buat aplikasi
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Tambahkan command handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("blast", blast))

    # Set command menu biar muncul otomatis di Telegram
    commands = [
        BotCommand("start", "Mulai bot"),
        BotCommand("help", "Bantuan"),
        BotCommand("blast", "Blast pesan ke channel"),
    ]
    await app.bot.set_my_commands(commands)

    logger.info("🚀 Bot berjalan...")
    await app.run_polling()


if __name__ == "__main__":
    asyncio.run(main())
