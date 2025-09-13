import logging
import asyncio
from telegram import Update, BotCommand
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# --- Konfigurasi Bot ---
TELEGRAM_BOT_TOKEN = "ISI_TOKEN_BOT_KAMU"   # ganti dengan token bot kamu
CHANNEL_USERNAME = "@promoshopee22a"        # username channel publik

# --- Logging ---
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- Command Handlers ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Halo! Pilih menu yang tersedia di bawah.")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "📖 Bantuan:\n"
        "/start - Mulai bot\n"
        "/help - Info bantuan\n"
        "/blast - Kirim pesan promo default ke channel\n"
        "/blastcustom <pesan> - Kirim pesan custom ke channel"
    )
    await update.message.reply_text(help_text)


async def blast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Blast pesan default ke channel"""
    try:
        pesan = "🔥 Promo terbaru! Klik di sini 👉 <a href='https://t.me/promoshopee22a'>Join Channel</a>"

        await context.bot.send_message(
            chat_id=CHANNEL_USERNAME,
            text=pesan,
            parse_mode="HTML",
            disable_web_page_preview=True
        )

        await update.message.reply_text("✅ Pesan blast default berhasil dikirim ke channel.")
    except Exception as e:
        logger.error(f"❌ Error mengirim ke channel: {e}")
        await update.message.reply_text(f"Gagal kirim pesan ke channel: {e}")


async def blast_custom(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Blast pesan sesuai input user"""
    try:
        if not context.args:
            await update.message.reply_text("⚠️ Format salah!\nGunakan: /blastcustom <pesan kamu>")
            return

        pesan = " ".join(context.args)

        await context.bot.send_message(
            chat_id=CHANNEL_USERNAME,
            text=pesan,
            parse_mode="HTML",
            disable_web_page_preview=True
        )

        await update.message.reply_text("✅ Pesan custom berhasil dikirim ke channel.")
    except Exception as e:
        logger.error(f"❌ Error blast custom: {e}")
        await update.message.reply_text(f"Gagal blast custom: {e}")


# --- Main ---
async def main():
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Handler perintah
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("blast", blast))
    app.add_handler(CommandHandler("blastcustom", blast_custom))

    # Set menu command otomatis
    commands = [
        BotCommand("start", "Mulai bot"),
        BotCommand("help", "Bantuan"),
        BotCommand("blast", "Blast pesan default ke channel"),
        BotCommand("blastcustom", "Blast pesan custom ke channel"),
    ]
    await app.bot.set_my_commands(commands)

    logger.info("🤖 Bot berjalan... tekan CTRL+C untuk berhenti.")
    await app.run_polling()


if __name__ == "__main__":
    asyncio.run(main())
