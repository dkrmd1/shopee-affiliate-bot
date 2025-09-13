# Bot Shopee Affiliate dengan Channel Publik untuk Railway
# File: main.py

import os
import logging
import sqlite3
import time
import requests
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    BotCommand,
    ChatMember
)
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
)

# ========== LOGGING ==========
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ========== CONFIG ==========
HARDCODED_CONFIG = {
    'BOT_TOKEN': '8324792358:AAGXjXwm1U5cBs5c5Gd8VA3KVtYfxPVSPWA',
    'ADMIN_ID': 1239490619,
    'CHANNEL_ID': '@promoshopee22a',  # bisa pakai @username atau -100xxxxxxxx
    'CHANNEL_USERNAME': '@promoshopee22a'
}

BOT_TOKEN = os.getenv('BOT_TOKEN') or HARDCODED_CONFIG['BOT_TOKEN']
ADMIN_ID = int(os.getenv('ADMIN_ID', str(HARDCODED_CONFIG['ADMIN_ID'])))
CHANNEL_ID = os.getenv('CHANNEL_ID') or HARDCODED_CONFIG['CHANNEL_ID']
CHANNEL_USERNAME = os.getenv('CHANNEL_USERNAME') or HARDCODED_CONFIG['CHANNEL_USERNAME']

# ========== DB INIT ==========
def init_db():
    conn = sqlite3.connect('shopee_affiliate.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS produk (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nama TEXT NOT NULL,
            harga_asli INTEGER,
            harga_promo INTEGER,
            link_affiliate TEXT NOT NULL,
            dibuat_pada TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

# ========== HELPER ==========
def format_rupiah(nominal: int) -> str:
    return f"Rp {nominal:,}".replace(",", ".")

async def cek_subscribe(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    try:
        member = await context.bot.get_chat_member(CHANNEL_ID, user_id)
        return member.status in [ChatMember.MEMBER, ChatMember.ADMINISTRATOR, ChatMember.OWNER]
    except Exception as e:
        logger.warning(f"⚠️ Cek subscribe gagal: {e}")
        return True

# ========== COMMANDS ==========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    nama = update.effective_user.first_name or "Kak"
    pesan = f"""
🛍️ Selamat datang {nama} di **Bot Promo Shopee**!

Pilih menu untuk melihat promo:
🔥 Promo Hari Ini
⚡ Flash Sale
📦 Stok Terbatas
    """
    keyboard = [
        [InlineKeyboardButton("🔥 Promo Hari Ini", callback_data="promo_hari_ini")],
        [InlineKeyboardButton("📢 Channel Promo", url=f"https://t.me/{CHANNEL_USERNAME[1:]}")]
    ]
    await update.message.reply_text(
        pesan, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pesan = f"""
🤖 **Info Bot Shopee Affiliate**

✅ Status: ONLINE
👤 Admin ID: {ADMIN_ID}
📢 Channel: {CHANNEL_USERNAME}

Commands:
• /start - Mulai
• /promo - Lihat promo
• /info - Info bot
• /tambah - Tambah produk (Admin)
• /blast - Blast produk (Admin)
    """
    await update.message.reply_text(pesan, parse_mode="Markdown")

async def promo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    conn = sqlite3.connect('shopee_affiliate.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("SELECT nama, harga_asli, harga_promo, link_affiliate FROM produk ORDER BY dibuat_pada DESC LIMIT 5")
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        await update.message.reply_text("⚠️ Belum ada produk promo.")
        return

    for nama, harga_asli, harga_promo, link in rows:
        teks = f"""
**{nama}**
💰 Harga Asli: {format_rupiah(harga_asli)}
💸 Harga Promo: {format_rupiah(harga_promo)}

👉 [Beli Sekarang]({link})
        """
        await update.message.reply_text(teks, parse_mode="Markdown")

async def tambah(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⚠️ Kamu bukan admin!")
        return

    if len(context.args) < 4:
        await update.message.reply_text("📌 Format: /tambah <nama> <harga_asli> <harga_promo> <link>")
        return

    nama = context.args[0]
    harga_asli = int(context.args[1])
    harga_promo = int(context.args[2])
    link = context.args[3]

    conn = sqlite3.connect('shopee_affiliate.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO produk (nama, harga_asli, harga_promo, link_affiliate) VALUES (?, ?, ?, ?)",
        (nama, harga_asli, harga_promo, link)
    )
    conn.commit()
    conn.close()

    await update.message.reply_text(f"✅ Produk *{nama}* berhasil ditambahkan!", parse_mode="Markdown")

async def blast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⚠️ Kamu bukan admin!")
        return

    conn = sqlite3.connect('shopee_affiliate.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("SELECT nama, harga_asli, harga_promo, link_affiliate FROM produk ORDER BY dibuat_pada DESC LIMIT 1")
    produk = cursor.fetchone()
    conn.close()

    if not produk:
        await update.message.reply_text("⚠️ Tidak ada produk untuk diblast.")
        return

    nama, harga_asli, harga_promo, link = produk
    teks = f"""
🔥 PROMO TERBARU! 🔥

**{nama}**
💰 Harga Asli: {format_rupiah(harga_asli)}
💸 Harga Promo: {format_rupiah(harga_promo)}

👉 [Klik untuk beli]({link})
    """
    try:
        await context.bot.send_message(
            chat_id=CHANNEL_ID,
            text=teks,
            parse_mode="Markdown"
        )
        await update.message.reply_text("✅ Produk berhasil diblast ke channel!")
    except Exception as e:
        await update.message.reply_text(f"❌ Gagal ngeblast: {e}")

# ========== MAIN ==========
def main():
    init_db()

    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/deleteWebhook"
        requests.post(url, json={"drop_pending_updates": True}, timeout=10)
        time.sleep(2)
    except:
        pass

    app = Application.builder().token(BOT_TOKEN).build()

    # daftar handler
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("info", info))
    app.add_handler(CommandHandler("promo", promo))
    app.add_handler(CommandHandler("tambah", tambah))
    app.add_handler(CommandHandler("blast", blast))

    # set command menu biar muncul di Telegram
    async def post_init(application: Application):
        await application.bot.set_my_commands([
            BotCommand("start", "Mulai bot"),
            BotCommand("info", "Info bot"),
            BotCommand("promo", "Lihat promo"),
            BotCommand("tambah", "Tambah produk (Admin)"),
            BotCommand("blast", "Blast ke channel (Admin)")
        ])

    app.post_init = post_init

    app.run_polling()

if __name__ == "__main__":
    main()
