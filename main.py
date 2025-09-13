import os
import logging
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup
)
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    ContextTypes
)

# 🔑 Ambil token & config dari environment Railway
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = os.getenv("ADMIN_ID")
CHANNEL_ID = os.getenv("CHANNEL_ID", "@promoshopee22a")

# 🚨 Logging biar gampang debug
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)


# ==========================
# MENU UTAMA
# ==========================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    # Tombol menu
    keyboard = [
        [InlineKeyboardButton("🔥 Promo Hari Ini", callback_data="promo")],
        [InlineKeyboardButton("⚡ Flash Sale", callback_data="flashsale")],
        [InlineKeyboardButton("📂 Pilih Kategori", callback_data="kategori")],
        [InlineKeyboardButton("ℹ️ Bantuan", callback_data="bantuan")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        f"Halo {user.first_name}! 👋\n"
        f"Selamat datang di Bot Promo Shopee!\n\n"
        f"📢 Pastikan sudah join channel {CHANNEL_ID} untuk akses penuh.",
        reply_markup=reply_markup
    )


# ==========================
# HANDLER PILIHAN MENU
# ==========================
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "promo":
        await query.edit_message_text("🔥 Promo hari ini: \n1. Produk A\n2. Produk B")
    elif query.data == "flashsale":
        await query.edit_message_text("⚡ Flash Sale aktif sekarang!")
    elif query.data == "kategori":
        # Submenu kategori
        kategori_keyboard = [
            [InlineKeyboardButton("📱 Elektronik", callback_data="cat_elektronik")],
            [InlineKeyboardButton("👕 Fashion", callback_data="cat_fashion")],
            [InlineKeyboardButton("🏠 Rumah Tangga", callback_data="cat_rumah")],
            [InlineKeyboardButton("⬅️ Kembali", callback_data="back_main")]
        ]
        await query.edit_message_text(
            "📂 Pilih kategori favorit kamu:",
            reply_markup=InlineKeyboardMarkup(kategori_keyboard)
        )
    elif query.data == "bantuan":
        await query.edit_message_text("ℹ️ Gunakan menu untuk lihat promo & flash sale.")
    elif query.data == "back_main":
        await start(update, context)
    else:
        await query.edit_message_text("✅ Kategori tersimpan! Nanti promo akan sesuai pilihanmu.")


# ==========================
# MAIN FUNCTION
# ==========================
def main():
    if not BOT_TOKEN:
        raise ValueError("❌ BOT_TOKEN belum di-set di Railway Variables!")

    app = Application.builder().token(BOT_TOKEN).build()

    # Command
    app.add_handler(CommandHandler("start", start))

    # Callback Button
    app.add_handler(CallbackQueryHandler(button_handler))

    logger.info("🤖 Bot berjalan...")
    app.run_polling()


if __name__ == "__main__":
    main()
