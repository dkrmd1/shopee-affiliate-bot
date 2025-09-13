#!/usr/bin/env python3
# bot.py
import os
import asyncio
import logging
import sqlite3
from datetime import datetime
import pytz
from functools import wraps

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from telegram import Update, ChatMemberStatus, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# ------------- CONFIG -------------
BOT_TOKEN = os.environ.get("BOT_TOKEN")           # token BotFather
ADMIN_ID = int(os.environ.get("ADMIN_ID", "0"))  # telegram id admin (angka)
CHANNEL_ID = os.environ.get("CHANNEL_ID")        # contoh: @namachannel atau -100xxxx
CHANNEL_USERNAME = os.environ.get("CHANNEL_USERNAME")  # @namachannel
TIMEZONE = "Asia/Jakarta"
DB_PATH = os.environ.get("DB_PATH", "botdata.db")
# -----------------------------------

# Logging
logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# ---------- DATABASE HELPERS ----------
def init_db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    cur = conn.cursor()
    # users: store chat_id, first_name, subscribed flag, fav_category
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER UNIQUE,
            username TEXT,
            first_name TEXT,
            subscribed INTEGER DEFAULT 0,
            fav_category TEXT
        )
        """
    )
    # products: admin adds products
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            category TEXT,
            price_old INTEGER,
            price_new INTEGER,
            url TEXT,
            description TEXT,
            is_flashsale INTEGER DEFAULT 0,
            auto_post INTEGER DEFAULT 1,
            created_at TEXT
        )
        """
    )
    conn.commit()
    return conn

DB = init_db()
DB_LOCK = asyncio.Lock()

async def db_execute(query, params=(), fetch=False):
    async with DB_LOCK:
        def _run():
            cur = DB.cursor()
            cur.execute(query, params)
            if fetch:
                res = cur.fetchall()
            else:
                res = None
            DB.commit()
            return res
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, _run)

# ---------- UTIL ----------
def admin_only(func):
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id if update.effective_user else None
        if user_id != ADMIN_ID:
            await update.message.reply_text("❌ Perintah ini hanya untuk admin.")
            return
        return await func(update, context)
    return wrapper

async def ensure_user(chat_id, user):
    # insert or update user basic info
    await db_execute(
        """
        INSERT INTO users (chat_id, username, first_name)
        VALUES (?, ?, ?)
        ON CONFLICT(chat_id) DO UPDATE SET username=excluded.username, first_name=excluded.first_name
        """,
        (chat_id, user.username or "", user.first_name or ""),
    )

async def check_subscribed(bot, user_chat_id):
    # return True if user is member of the channel
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_chat_id)
        status = member.status
        return status not in (ChatMemberStatus.LEFT, ChatMemberStatus.KICKED)
    except Exception as e:
        logger.warning("check_subscribed error: %s", e)
        return False  # if fail, treat as not subscribed

def format_product_row(row):
    # row: (id,title,category,price_old,price_new,url,description,is_flashsale,auto_post,created_at)
    id_, title, category, price_old, price_new, url, description, is_flashsale, auto_post, created_at = row
    price_old_str = f"Rp {price_old:,}" if price_old else "-"
    price_new_str = f"Rp {price_new:,}" if price_new else "-"
    fs = "⚡ FLASH SALE" if is_flashsale else ""
    s = f"*{title}* {fs}\nKategori: `{category}`\nHarga: ~~{price_old_str}~~ ➜ *{price_new_str}*\n{description}\n🔗 [Beli di Shopee]({url})\nID: `{id_}`\n"
    return s

# ---------- TELEGRAM HANDLERS ----------
async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat_id = update.effective_chat.id
    await ensure_user(chat_id, user)
    # check subscribe
    is_sub = await check_subscribed(context.bot, chat_id)
    await db_execute("UPDATE users SET subscribed = ? WHERE chat_id = ?", (1 if is_sub else 0, chat_id))
    kb = [
        [InlineKeyboardButton("Gabung Channel", url=f"https://t.me/{CHANNEL_USERNAME.lstrip('@')}")],
        [InlineKeyboardButton("Cek Promo Hari Ini", callback_data="promo_now")],
    ]
    txt = (
        f"Halo, {user.first_name} 👋\n\n"
        "Selamat datang di Bot Promo Shopee Affiliate.\n\n"
        "Sebelum lanjut, pastikan kamu sudah bergabung dengan channel kami untuk bisa melihat promo penuh."
    )
    await update.message.reply_text(txt, reply_markup=InlineKeyboardMarkup(kb))

async def kategori_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # show categories from products table
    rows = await db_execute("SELECT DISTINCT category FROM products WHERE category IS NOT NULL", fetch=True)
    categories = [r[0] for r in rows] if rows else []
    if not categories:
        await update.message.reply_text("Belum ada kategori. Admin belum menambahkan produk.")
        return
    kb = [[InlineKeyboardButton(cat, callback_data=f"setcat|{cat}")] for cat in categories]
    await update.message.reply_text("Pilih kategori favoritmu:", reply_markup=InlineKeyboardMarkup(kb))

async def promo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # show products for today (simple: newest 10)
    rows = await db_execute("SELECT * FROM products ORDER BY created_at DESC LIMIT 10", fetch=True)
    if not rows:
        await update.message.reply_text("Belum ada promo hari ini.")
        return
    for row in rows:
        txt = format_product_row(row)
        await update.message.reply_text(txt, parse_mode="Markdown", disable_web_page_preview=False)

async def flashsale_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    rows = await db_execute("SELECT * FROM products WHERE is_flashsale=1 ORDER BY created_at DESC", fetch=True)
    if not rows:
        await update.message.reply_text("Tidak ada flash sale aktif saat ini.")
        return
    for row in rows:
        txt = format_product_row(row)
        await update.message.reply_text(txt, parse_mode="Markdown", disable_web_page_preview=False)

# ----------- ADMIN COMMANDS ------------
@admin_only
async def cmd_tambah(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Expect: /tambah Title | Category | price_old | price_new | url | desc | is_flashsale | auto_post
    text = update.message.text
    # remove command prefix
    payload = text.partition(" ")[2].strip()
    if not payload:
        await update.message.reply_text("Format: /tambah Title | Category | price_old | price_new | url | desc | is_flashsale(0/1) | auto_post(0/1)")
        return
    parts = [p.strip() for p in payload.split("|")]
    # allow missing optional fields by padding
    while len(parts) < 8:
        parts.append("")
    title, category, price_old, price_new, url, desc, is_flashsale, auto_post = parts[:8]
    try:
        price_old_i = int(price_old) if price_old else 0
        price_new_i = int(price_new) if price_new else 0
        is_flashsale_i = 1 if is_flashsale == "1" else 0
        auto_post_i = 1 if auto_post != "0" else 0
    except Exception:
        await update.message.reply_text("Pastikan harga berupa angka (tanpa titik/komers). Contoh: 15999000")
        return
    created_at = datetime.now(pytz.timezone(TIMEZONE)).isoformat()
    await db_execute(
        "INSERT INTO products (title,category,price_old,price_new,url,description,is_flashsale,auto_post,created_at) VALUES (?,?,?,?,?,?,?,?,?)",
        (title, category, price_old_i, price_new_i, url, desc, is_flashsale_i, auto_post_i, created_at),
    )
    await update.message.reply_text("✅ Produk berhasil ditambahkan.")

@admin_only
async def cmd_lihat_produk(update: Update, context: ContextTypes.DEFAULT_TYPE):
    rows = await db_execute("SELECT * FROM products ORDER BY created_at DESC", fetch=True)
    if not rows:
        await update.message.reply_text("Belum ada produk.")
        return
    txt = "Daftar produk:\n\n"
    for r in rows:
        txt += f"ID: {r[0]} | {r[1]} | {r[2]} | Rp {r[4]:,}\n"
    await update.message.reply_text(txt)

@admin_only
async def cmd_kirim_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # /kirim_channel {id}
    parts = update.message.text.split()
    if len(parts) < 2:
        await update.message.reply_text("Format: /kirim_channel {id}")
        return
    pid = parts[1]
    try:
        pid = int(pid)
    except:
        await update.message.reply_text("ID harus angka.")
        return
    row = await db_execute("SELECT * FROM products WHERE id = ?", (pid,), fetch=True)
    if not row:
        await update.message.reply_text("Produk tidak ditemukan.")
        return
    row = row[0]
    txt = format_product_row(row)
    try:
        await context.bot.send_message(chat_id=CHANNEL_ID, text=txt, parse_mode="Markdown", disable_web_page_preview=False)
        await update.message.reply_text("✅ Produk dikirim ke channel.")
    except Exception as e:
        logger.exception("kirim_channel error")
        await update.message.reply_text(f"Error mengirim ke channel: {e}")

@admin_only
async def cmd_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # /broadcast {id}
    parts = update.message.text.split()
    if len(parts) < 2:
        await update.message.reply_text("Format: /broadcast {product_id}")
        return
    try:
        pid = int(parts[1])
    except:
        await update.message.reply_text("ID produk harus angka.")
        return
    row = await db_execute("SELECT * FROM products WHERE id = ?", (pid,), fetch=True)
    if not row:
        await update.message.reply_text("Produk tidak ditemukan.")
        return
    row = row[0]
    txt = format_product_row(row)
    # get users subscribed
    users = await db_execute("SELECT chat_id FROM users WHERE subscribed=1", fetch=True)
    if not users:
        await update.message.reply_text("Tidak ada user yang terdaftar/ter-subscribe.")
        return
    sent = 0
    failed = 0
    for (chat_id,) in users:
        try:
            await context.bot.send_message(chat_id=chat_id, text=txt, parse_mode="Markdown", disable_web_page_preview=False)
            sent += 1
            await asyncio.sleep(0.05)  # slight throttle
        except Exception as e:
            logger.warning("broadcast to %s failed: %s", chat_id, e)
            failed += 1
    await update.message.reply_text(f"Broadcast selesai. Terkirim: {sent}. Gagal: {failed}.")

# --------- SCHEDULER TASKS ----------
async def scheduled_broadcast_all(context: ContextTypes.DEFAULT_TYPE):
    # send top 5 newest products to subscribers
    rows = await db_execute("SELECT * FROM products ORDER BY created_at DESC LIMIT 5", fetch=True)
    if not rows:
        logger.info("Scheduled broadcast: no products to send.")
        return
    txts = [format_product_row(r) for r in rows]
    users = await db_execute("SELECT chat_id FROM users WHERE subscribed=1", fetch=True)
    if not users:
        logger.info("Scheduled broadcast: no subscribed users.")
        return
    for (chat_id,) in users:
        for txt in txts:
            try:
                await context.bot.send_message(chat_id=chat_id, text=txt, parse_mode="Markdown", disable_web_page_preview=False)
                await asyncio.sleep(0.05)
            except Exception as e:
                logger.warning("scheduled send fail %s: %s", chat_id, e)

# ---------- CALLBACKS ----------
async def callback_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    data = q.data or ""
    if data == "promo_now":
        # call promo
        await promo_handler(update, context)
        return
    if data.startswith("setcat|"):
        cat = data.split("|", 1)[1]
        chat_id = q.message.chat.id
        await db_execute("UPDATE users SET fav_category = ? WHERE chat_id = ?", (cat, chat_id))
        await q.edit_message_text(f"Kategori favorit disimpan: {cat}")

# ---------- START APP ----------
async def main():
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN belum di-set.")
    application = Application.builder().token(BOT_TOKEN).concurrent_updates(True).build()

    # handlers
    application.add_handler(CommandHandler("start", start_handler))
    application.add_handler(CommandHandler("kategori", kategori_handler))
    application.add_handler(CommandHandler("promo", promo_handler))
    application.add_handler(CommandHandler("flashsale", flashsale_handler))

    # admin
    application.add_handler(CommandHandler("tambah", cmd_tambah))
    application.add_handler(CommandHandler("lihat_produk", cmd_lihat_produk))
    application.add_handler(CommandHandler("kirim_channel", cmd_kirim_channel))
    application.add_handler(CommandHandler("broadcast", cmd_broadcast))

    application.add_handler(MessageHandler(filters.ALL & filters.TEXT, lambda u,c: None))  # noop to keep app alive for text
    application.add_handler(MessageHandler(filters.StatusUpdate.LEFT_CHAT_MEMBER, lambda u,c: None))
    application.add_handler(application.callback_query_handler(callback_query_handler))

    # scheduler
    scheduler = AsyncIOScheduler(timezone=pytz.timezone(TIMEZONE))
    # two daily broadcasts at 08:00 and 20:00
    scheduler.add_job(lambda: application.create_task(scheduled_broadcast_all(application.bot)), CronTrigger(hour=8, minute=0))
    scheduler.add_job(lambda: application.create_task(scheduled_broadcast_all(application.bot)), CronTrigger(hour=20, minute=0))
    scheduler.start()

    logger.info("Bot starting...")
    await application.run_polling()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Stopping...")
