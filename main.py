import logging
import sqlite3
import asyncio
import os
from datetime import datetime, time
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup
)
from telegram.constants import ChatMemberStatus, ParseMode
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    filters, ContextTypes
)

# --- Konfigurasi dari ENV ---
BOT_TOKEN = os.getenv("BOT_TOKEN", "ISI_TOKEN_BOT")
ADMIN_ID = int(os.getenv("ADMIN_ID", "123456789"))
CHANNEL_ID = os.getenv("CHANNEL_ID", "@promoshopee22a")
CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME", "@promoshopee22a")

# --- Logging ---
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- Database ---
def init_db():
    conn = sqlite3.connect("db.sqlite3")
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS produk (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nama TEXT,
        kategori TEXT,
        harga_awal INTEGER,
        harga_diskon INTEGER,
        link TEXT,
        deskripsi TEXT,
        flashsale INTEGER DEFAULT 0,
        aktif INTEGER DEFAULT 1
    )
    """)
    conn.commit()
    conn.close()

# --- Format Produk ---
def format_produk(p):
    return (
        f"🛍️ <b>{p[1]}</b>\n"
        f"📂 Kategori: {p[2]}\n"
        f"💰 Harga Awal: Rp {p[3]:,}\n"
        f"🔥 Harga Promo: Rp {p[4]:,}\n"
        f"📌 Deskripsi: {p[6]}\n\n"
        f"👉 <a href='{p[5]}'>Beli Sekarang</a>"
    )

# --- Cek Subscribe ---
async def check_subscribe(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    try:
        member = await context.bot.get_chat_member(CHANNEL_USERNAME, user_id)
        return member.status in [
            ChatMemberStatus.MEMBER,
            ChatMemberStatus.ADMINISTRATOR,
            ChatMemberStatus.OWNER
        ]
    except Exception as e:
        logger.error(f"Check subscribe error: {e}")
        return False

# --- Command: Start ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not await check_subscribe(user_id, context):
        keyboard = [[InlineKeyboardButton("Join Channel", url=f"https://t.me/{CHANNEL_USERNAME.lstrip('@')}")]]
        await update.message.reply_text(
            "⚠️ Kamu harus join channel dulu untuk pakai bot ini!",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    await update.message.reply_text(
        "Selamat datang di Shopee Affiliate Bot 🛍️\n\n"
        "Gunakan /promo untuk lihat promo hari ini, /flashsale untuk cek flash sale."
    )

# --- Command: Tambah Produk (Admin) ---
async def tambah(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    try:
        data = " ".join(context.args).split("|")
        nama, kategori, harga_awal, harga_diskon, link, deskripsi, flashsale, aktif = [d.strip() for d in data]

        conn = sqlite3.connect("db.sqlite3")
        cur = conn.cursor()
        cur.execute("INSERT INTO produk (nama,kategori,harga_awal,harga_diskon,link,deskripsi,flashsale,aktif) VALUES (?,?,?,?,?,?,?,?)",
                    (nama, kategori, int(harga_awal), int(harga_diskon), link, deskripsi, int(flashsale), int(aktif)))
        conn.commit()
        conn.close()

        await update.message.reply_text(f"✅ Produk '{nama}' berhasil ditambahkan!")
    except Exception as e:
        await update.message.reply_text("❌ Format salah.\nGunakan:\n/tambah Nama | Kategori | Harga1 | Harga2 | Link | Deskripsi | 0 | 1")
        logger.error(e)

# --- Command: Lihat Produk ---
async def lihat_produk(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    conn = sqlite3.connect("db.sqlite3")
    cur = conn.cursor()
    cur.execute("SELECT * FROM produk")
    rows = cur.fetchall()
    conn.close()

    if not rows:
        await update.message.reply_text("❌ Belum ada produk.")
        return

    text = "\n\n".join([f"{r[0]}. {r[1]} | {r[2]} | Rp {r[4]:,}" for r in rows])
    await update.message.reply_text(text)

# --- Command: Kirim ke Channel ---
async def kirim_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    try:
        pid = int(context.args[0])
        conn = sqlite3.connect("db.sqlite3")
        cur = conn.cursor()
        cur.execute("SELECT * FROM produk WHERE id=?", (pid,))
        p = cur.fetchone()
        conn.close()

        if not p:
            await update.message.reply_text("❌ Produk tidak ditemukan.")
            return

        await context.bot.send_message(
            chat_id=CHANNEL_ID,
            text=format_produk(p),
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=False
        )
        await update.message.reply_text("✅ Produk dikirim ke channel.")
    except Exception as e:
        logger.error(e)

# --- Command: Broadcast ---
async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    try:
        pid = int(context.args[0])
        conn = sqlite3.connect("db.sqlite3")
        cur = conn.cursor()
        cur.execute("SELECT * FROM produk WHERE id=?", (pid,))
        p = cur.fetchone()
        conn.close()

        if not p:
            await update.message.reply_text("❌ Produk tidak ditemukan.")
            return

        # Broadcast ke semua user yang pernah start
        # (contoh: simpan user_id ke DB, belum diimplementasi penuh)
        await update.message.reply_text("🚧 Broadcast dummy: Fitur DB user bisa ditambah.")

    except Exception as e:
        logger.error(e)

# --- Command: Promo ---
async def promo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    conn = sqlite3.connect("db.sqlite3")
    cur = conn.cursor()
    cur.execute("SELECT * FROM produk WHERE aktif=1 LIMIT 5")
    rows = cur.fetchall()
    conn.close()

    if not rows:
        await update.message.reply_text("❌ Tidak ada promo.")
        return

    for p in rows:
        await update.message.reply_text(format_produk(p), parse_mode=ParseMode.HTML, disable_web_page_preview=False)

# --- Command: Flash Sale ---
async def flashsale(update: Update, context: ContextTypes.DEFAULT_TYPE):
    conn = sqlite3.connect("db.sqlite3")
    cur = conn.cursor()
    cur.execute("SELECT * FROM produk WHERE flashsale=1 AND aktif=1")
    rows = cur.fetchall()
    conn.close()

    if not rows:
        await update.message.reply_text("❌ Tidak ada flash sale.")
        return

    for p in rows:
        await update.message.reply_text(format_produk(p), parse_mode=ParseMode.HTML)

# --- Jadwal Otomatis (08:00 & 20:00) ---
async def schedule_jobs(app: Application):
    async def job():
        conn = sqlite3.connect("db.sqlite3")
        cur = conn.cursor()
        cur.execute("SELECT * FROM produk WHERE aktif=1 LIMIT 1")
        p = cur.fetchone()
        conn.close()

        if p:
            await app.bot.send_message(CHANNEL_ID, text=format_produk(p), parse_mode=ParseMode.HTML)

    aiosched = app.job_queue
    aiosched.run_daily(job, time(hour=8, minute=0))
    aiosched.run_daily(job, time(hour=20, minute=0))

# --- Main ---
async def main():
    init_db()
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("tambah", tambah))
    app.add_handler(CommandHandler("lihat_produk", lihat_produk))
    app.add_handler(CommandHandler("kirim_channel", kirim_channel))
    app.add_handler(CommandHandler("broadcast", broadcast))
    app.add_handler(CommandHandler("promo", promo))
    app.add_handler(CommandHandler("flashsale", flashsale))

    await schedule_jobs(app)
    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
