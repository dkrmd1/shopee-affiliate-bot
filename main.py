import os
import sqlite3
import logging
from datetime import datetime
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    Application, CommandHandler, CallbackContext,
    CallbackQueryHandler, MessageHandler, filters
)
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# Load env
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
CHANNEL_ID = os.getenv("CHANNEL_ID")
CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME")

if not BOT_TOKEN:
    raise ValueError("❌ BOT_TOKEN belum di-set di Railway Variables!")

# Logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# DB Setup
conn = sqlite3.connect("db.sqlite3", check_same_thread=False)
cur = conn.cursor()
cur.execute("""
CREATE TABLE IF NOT EXISTS produk (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nama TEXT,
    kategori TEXT,
    harga_asli INTEGER,
    harga_diskon INTEGER,
    link TEXT,
    deskripsi TEXT,
    flashsale INTEGER DEFAULT 0,
    aktif INTEGER DEFAULT 1
)
""")
conn.commit()

# ========== BOT FEATURES ==========
async def start(update: Update, context: CallbackContext):
    user = update.effective_user
    chat_id = update.effective_chat.id

    # cek subscribe
    keyboard = [
        [InlineKeyboardButton("📢 Join Channel", url=f"https://t.me/{CHANNEL_USERNAME}")],
        [InlineKeyboardButton("✅ Cek Subscribe", callback_data="cek_subscribe")]
    ]
    await context.bot.send_message(
        chat_id=chat_id,
        text=f"Halo {user.first_name}! 🎉\n\nWajib join channel {CHANNEL_USERNAME} dulu ya sebelum pakai bot ini.",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def cek_subscribe(update: Update, context: CallbackContext):
    query = update.callback_query
    user_id = query.from_user.id
    member = await context.bot.get_chat_member(CHANNEL_ID, user_id)

    if member.status in ["member", "administrator", "creator"]:
        keyboard = [
            [InlineKeyboardButton("🔥 Promo Hari Ini", callback_data="promo")],
            [InlineKeyboardButton("⚡ Flash Sale", callback_data="flashsale")],
            [InlineKeyboardButton("📂 Kategori", callback_data="kategori")]
        ]
        await query.edit_message_text(
            text="✅ Kamu sudah subscribe! Pilih menu di bawah:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    else:
        await query.answer("❌ Belum join channel!", show_alert=True)

# ========== ADMIN COMMANDS ==========
async def tambah(update: Update, context: CallbackContext):
    if update.effective_user.id != ADMIN_ID:
        return
    try:
        data = " ".join(context.args).split("|")
        nama, kategori, harga_asli, harga_diskon, link, deskripsi, flashsale, aktif = [x.strip() for x in data]
        cur.execute("INSERT INTO produk (nama,kategori,harga_asli,harga_diskon,link,deskripsi,flashsale,aktif) VALUES (?,?,?,?,?,?,?,?)",
                    (nama, kategori, int(harga_asli), int(harga_diskon), link, deskripsi, int(flashsale), int(aktif)))
        conn.commit()
        await update.message.reply_text("✅ Produk berhasil ditambahkan!")
    except Exception as e:
        await update.message.reply_text(f"❌ Format salah!\n{e}")

async def lihat_produk(update: Update, context: CallbackContext):
    if update.effective_user.id != ADMIN_ID:
        return
    cur.execute("SELECT * FROM produk ORDER BY id DESC LIMIT 10")
    rows = cur.fetchall()
    if not rows:
        await update.message.reply_text("❌ Belum ada produk")
        return
    msg = "📦 Daftar Produk:\n\n"
    for r in rows:
        msg += f"#{r[0]} {r[1]} | {r[2]} | Rp{r[4]:,}\n"
    await update.message.reply_text(msg)

async def kirim_channel(update: Update, context: CallbackContext):
    if update.effective_user.id != ADMIN_ID:
        return
    try:
        pid = int(context.args[0])
        cur.execute("SELECT * FROM produk WHERE id=?", (pid,))
        p = cur.fetchone()
        if not p:
            await update.message.reply_text("❌ Produk tidak ditemukan")
            return
        text = f"🛍️ <b>{p[1]}</b>\n\nKategori: {p[2]}\nHarga: Rp{p[3]:,} → <b>Rp{p[4]:,}</b>\n\n{p[6]}\n\n👉 <a href='{p[5]}'>Beli Sekarang</a>"
        await context.bot.send_message(CHANNEL_ID, text, parse_mode="HTML", disable_web_page_preview=False)
        await update.message.reply_text("✅ Produk dikirim ke channel")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")

# ========== USER MENU ==========
async def menu_handler(update: Update, context: CallbackContext):
    query = update.callback_query
    data = query.data

    if data == "promo":
        cur.execute("SELECT * FROM produk WHERE aktif=1 ORDER BY id DESC LIMIT 5")
        rows = cur.fetchall()
        if not rows:
            await query.answer("❌ Belum ada promo")
            return
        for p in rows:
            text = f"🛍️ <b>{p[1]}</b>\n\nHarga: Rp{p[3]:,} → <b>Rp{p[4]:,}</b>\n\n{p[6]}\n\n👉 <a href='{p[5]}'>Beli Sekarang</a>"
            await context.bot.send_message(query.message.chat.id, text, parse_mode="HTML", disable_web_page_preview=False)

    elif data == "flashsale":
        cur.execute("SELECT * FROM produk WHERE flashsale=1 AND aktif=1")
        rows = cur.fetchall()
        if not rows:
            await query.answer("❌ Tidak ada flash sale")
            return
        for p in rows:
            text = f"⚡ <b>{p[1]}</b>\n\nHarga: Rp{p[3]:,} → <b>Rp{p[4]:,}</b>\n\n{p[6]}\n\n👉 <a href='{p[5]}'>Beli Cepat</a>"
            await context.bot.send_message(query.message.chat.id, text, parse_mode="HTML", disable_web_page_preview=False)

    elif data == "kategori":
        cur.execute("SELECT DISTINCT kategori FROM produk")
        rows = cur.fetchall()
        if not rows:
            await query.answer("❌ Tidak ada kategori")
            return
        buttons = [[InlineKeyboardButton(r[0], callback_data=f"cat_{r[0]}")] for r in rows]
        await query.edit_message_text("📂 Pilih kategori:", reply_markup=InlineKeyboardMarkup(buttons))

    elif data.startswith("cat_"):
        kategori = data.split("_", 1)[1]
        cur.execute("SELECT * FROM produk WHERE kategori=? AND aktif=1", (kategori,))
        rows = cur.fetchall()
        if not rows:
            await query.answer("❌ Belum ada produk kategori ini")
            return
        for p in rows:
            text = f"📦 <b>{p[1]}</b>\n\nHarga: Rp{p[3]:,} → <b>Rp{p[4]:,}</b>\n\n{p[6]}\n\n👉 <a href='{p[5]}'>Beli</a>"
            await context.bot.send_message(query.message.chat.id, text, parse_mode="HTML", disable_web_page_preview=False)

# ========== SCHEDULED JOBS ==========
async def broadcast_promo(context: CallbackContext):
    cur.execute("SELECT * FROM produk WHERE aktif=1 ORDER BY id DESC LIMIT 3")
    rows = cur.fetchall()
    if not rows:
        return
    for p in rows:
        text = f"🛍️ <b>{p[1]}</b>\nHarga: Rp{p[3]:,} → <b>Rp{p[4]:,}</b>\n\n👉 <a href='{p[5]}'>Beli Sekarang</a>"
        await context.bot.send_message(CHANNEL_ID, text, parse_mode="HTML", disable_web_page_preview=False)

# ========== MAIN ==========
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    # Commands
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("tambah", tambah))
    app.add_handler(CommandHandler("lihat_produk", lihat_produk))
    app.add_handler(CommandHandler("kirim_channel", kirim_channel))

    # Callback buttons
    app.add_handler(CallbackQueryHandler(cek_subscribe, pattern="cek_subscribe"))
    app.add_handler(CallbackQueryHandler(menu_handler))

    # Scheduler: 8 pagi & 8 malam
    scheduler = AsyncIOScheduler()
    scheduler.add_job(broadcast_promo, "cron", hour=8, minute=0, args=[app.bot])
    scheduler.add_job(broadcast_promo, "cron", hour=20, minute=0, args=[app.bot])
    scheduler.start()

    logging.info("🤖 Bot Shopee Affiliate aktif...")
    app.run_polling()

if __name__ == "__main__":
    main()
