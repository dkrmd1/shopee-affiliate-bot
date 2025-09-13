import logging
import sqlite3
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.constants import ChatMemberStatus
from telegram.ext import (
    Application, CommandHandler, ContextTypes, MessageHandler, filters
)
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import time

# --- Konfigurasi Bot ---
BOT_TOKEN = "ISI_TOKEN_BOT_KAMU"       # ganti dengan token BotFather
CHANNEL_USERNAME = "@promoshopee22a"   # ganti dengan channel publik
ADMIN_ID = 123456789                   # ganti dengan Telegram ID admin

# --- Logging ---
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- Database ---
DB_NAME = "produk.db"


def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS produk (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nama TEXT,
            kategori TEXT,
            harga_asli INTEGER,
            harga_diskon INTEGER,
            link TEXT,
            deskripsi TEXT,
            flashsale INTEGER,
            aktif INTEGER
        )
    """)
    conn.commit()
    conn.close()


# --- Command: Start ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat_member = await context.bot.get_chat_member(CHANNEL_USERNAME, user.id)

    if chat_member.status in [ChatMemberStatus.MEMBER, ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]:
        await update.message.reply_text(
            f"Halo {user.first_name}! 👋\n"
            f"Selamat datang di Shopee Affiliate Bot.\n"
            f"Gunakan /promo untuk lihat promo terbaru."
        )
    else:
        keyboard = [
            [InlineKeyboardButton("Join Channel", url=f"https://t.me/{CHANNEL_USERNAME.lstrip('@')}")]
        ]
        await update.message.reply_text(
            "⚠️ Kamu belum join channel! Silakan join dulu:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )


# --- Command: Tambah Produk (Admin) ---
async def tambah(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return await update.message.reply_text("❌ Kamu bukan admin.")

    try:
        data = " ".join(context.args).split("|")
        nama, kategori, harga_asli, harga_diskon, link, deskripsi, flashsale, aktif = [x.strip() for x in data]

        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute(
            "INSERT INTO produk (nama, kategori, harga_asli, harga_diskon, link, deskripsi, flashsale, aktif) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (nama, kategori, int(harga_asli), int(harga_diskon), link, deskripsi, int(flashsale), int(aktif))
        )
        conn.commit()
        conn.close()

        await update.message.reply_text(f"✅ Produk '{nama}' berhasil ditambahkan.")
    except Exception as e:
        await update.message.reply_text(f"❌ Format salah. Contoh:\n/tambah iPhone 15 | Elektronik | 15999000 | 12999000 | https://shopee.co.id/... | Garansi resmi | 0 | 1\n\nError: {e}")


# --- Command: Lihat Produk ---
async def lihat_produk(update: Update, context: ContextTypes.DEFAULT_TYPE):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT id, nama, kategori, harga_asli, harga_diskon FROM produk WHERE aktif=1")
    rows = c.fetchall()
    conn.close()

    if not rows:
        return await update.message.reply_text("❌ Belum ada produk aktif.")

    text = "📦 Daftar Produk Aktif:\n\n"
    for r in rows:
        text += f"#{r[0]} - {r[1]} ({r[2]})\n💰 {r[3]} → {r[4]}\n\n"

    await update.message.reply_text(text)


# --- Command: Kirim ke Channel ---
async def kirim_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return await update.message.reply_text("❌ Kamu bukan admin.")

    try:
        produk_id = int(context.args[0])
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("SELECT nama, kategori, harga_asli, harga_diskon, link, deskripsi FROM produk WHERE id=?", (produk_id,))
        row = c.fetchone()
        conn.close()

        if not row:
            return await update.message.reply_text("❌ Produk tidak ditemukan.")

        text = f"🔥 <b>{row[0]}</b>\n📂 {row[1]}\n💰 Rp {row[2]} → Rp {row[3]}\n\n{row[5]}\n\n👉 <a href='{row[4]}'>Beli Sekarang</a>"

        await context.bot.send_message(
            chat_id=CHANNEL_USERNAME,
            text=text,
            parse_mode="HTML",
            disable_web_page_preview=False
        )
        await update.message.reply_text("✅ Produk berhasil dikirim ke channel.")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")


# --- Command: Broadcast ---
async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return await update.message.reply_text("❌ Kamu bukan admin.")

    try:
        produk_id = int(context.args[0])
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("SELECT nama, kategori, harga_asli, harga_diskon, link, deskripsi FROM produk WHERE id=?", (produk_id,))
        row = c.fetchone()
        conn.close()

        if not row:
            return await update.message.reply_text("❌ Produk tidak ditemukan.")

        text = f"📢 Promo Spesial!\n\n🔥 <b>{row[0]}</b>\n📂 {row[1]}\n💰 Rp {row[2]} → Rp {row[3]}\n\n{row[5]}\n\n👉 <a href='{row[4]}'>Beli Sekarang</a>"

        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=text,
            parse_mode="HTML",
            disable_web_page_preview=False
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")


# --- Command: Promo Harian ---
async def promo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📢 Promo hari ini dikirim otomatis jam 08:00 & 20:00 ke channel.")


# --- Command: Flash Sale ---
async def flashsale(update: Update, context: ContextTypes.DEFAULT_TYPE):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT nama, harga_asli, harga_diskon, link FROM produk WHERE flashsale=1 AND aktif=1")
    rows = c.fetchall()
    conn.close()

    if not rows:
        return await update.message.reply_text("⚡ Tidak ada flash sale aktif.")

    text = "⚡ Flash Sale Aktif:\n\n"
    for r in rows:
        text += f"🔥 {r[0]}\n💰 Rp {r[1]} → Rp {r[2]}\n👉 {r[3]}\n\n"

    await update.message.reply_text(text)


# --- Scheduler untuk Promo Harian ---
def send_daily_promo(app: Application):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT nama, kategori, harga_asli, harga_diskon, link, deskripsi FROM produk WHERE aktif=1 LIMIT 1")
    row = c.fetchone()
    conn.close()

    if row:
        text = f"🌟 Promo Hari Ini!\n\n🔥 <b>{row[0]}</b>\n📂 {row[1]}\n💰 Rp {row[2]} → Rp {row[3]}\n\n{row[5]}\n\n👉 <a href='{row[4]}'>Beli Sekarang</a>"
        app.bot.send_message(chat_id=CHANNEL_USERNAME, text=text, parse_mode="HTML")


# --- Main ---
def main():
    init_db()
    app = Application.builder().token(BOT_TOKEN).build()

    # Command
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("tambah", tambah))
    app.add_handler(CommandHandler("lihat_produk", lihat_produk))
    app.add_handler(CommandHandler("kirim_channel", kirim_channel))
    app.add_handler(CommandHandler("broadcast", broadcast))
    app.add_handler(CommandHandler("promo", promo))
    app.add_handler(CommandHandler("flashsale", flashsale))

    # Jadwal otomatis (jam 08:00 & 20:00)
    scheduler = BackgroundScheduler(timezone="Asia/Jakarta")
    scheduler.add_job(lambda: send_daily_promo(app), trigger="cron", hour=8, minute=0)
    scheduler.add_job(lambda: send_daily_promo(app), trigger="cron", hour=20, minute=0)
    scheduler.start()

    logger.info("🤖 Bot berjalan...")
    app.run_polling()


if __name__ == "__main__":
    main()
