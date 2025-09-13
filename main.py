# Bot Shopee Affiliate dengan Channel Publik untuk Railway
# File: main.py

import os
import logging
import sqlite3
from datetime import datetime
import asyncio
import time
import requests

from telegram import (
    Update, 
    InlineKeyboardButton, 
    InlineKeyboardMarkup, 
    ChatMember, 
    Bot
)
from telegram.ext import (
    Application, 
    CommandHandler, 
    CallbackQueryHandler, 
    MessageHandler,
    ContextTypes,
    filters
)

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ================= CONFIG =================
HARDCODED_CONFIG = {
    'BOT_TOKEN': '8324792358:AAGXjXwm1U5cBs5c5Gd8VA3KVtYfxPVSPWA',
    'ADMIN_ID': 1239490619,
    'CHANNEL_ID': '@promoshopee22a', 
    'CHANNEL_USERNAME': '@promoshopee22a'
}

BOT_TOKEN = os.getenv('BOT_TOKEN') or HARDCODED_CONFIG['BOT_TOKEN']
ADMIN_ID = int(os.getenv('ADMIN_ID', str(HARDCODED_CONFIG['ADMIN_ID'])))
CHANNEL_ID = os.getenv('CHANNEL_ID') or HARDCODED_CONFIG['CHANNEL_ID']
CHANNEL_USERNAME = os.getenv('CHANNEL_USERNAME') or HARDCODED_CONFIG['CHANNEL_USERNAME']

logger.info(f"🔧 BOT_TOKEN: {BOT_TOKEN[:15]}***")
logger.info(f"🔧 ADMIN_ID: {ADMIN_ID}")
logger.info(f"🔧 CHANNEL_ID: {CHANNEL_ID}")
logger.info(f"🔧 CHANNEL_USERNAME: {CHANNEL_USERNAME}")

# ================= DATABASE =================
class ShopeeAffiliateBot:
    def __init__(self):
        self.init_database()
    
    def init_database(self):
        try:
            conn = sqlite3.connect('shopee_affiliate.db', check_same_thread=False)
            cursor = conn.cursor()
            
            # Produk
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS produk (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nama TEXT NOT NULL,
                    kategori TEXT,
                    harga_asli INTEGER,
                    harga_promo INTEGER,
                    diskon_persen INTEGER,
                    link_affiliate TEXT NOT NULL,
                    gambar_url TEXT,
                    deskripsi TEXT,
                    stok_terbatas BOOLEAN DEFAULT 0,
                    flash_sale BOOLEAN DEFAULT 0,
                    aktif BOOLEAN DEFAULT 1,
                    dibuat_pada TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Pengguna
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS pengguna (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    nama_depan TEXT,
                    bergabung_pada TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    subscribe_channel BOOLEAN DEFAULT 0,
                    notifikasi_aktif BOOLEAN DEFAULT 1,
                    terakhir_aktif TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            conn.commit()
            conn.close()
            logger.info("✅ Database siap digunakan")
            
        except Exception as e:
            logger.error(f"❌ Error DB init: {e}")
            raise e

# ================= HELPER =================
async def cek_subscribe_channel(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    try:
        member = await context.bot.get_chat_member(CHANNEL_ID, user_id)
        return member.status in [ChatMember.MEMBER, ChatMember.ADMINISTRATOR, ChatMember.OWNER]
    except Exception as e:
        logger.warning(f"⚠️ Cek subscribe gagal user {user_id}: {e}")
        return True  # biar lolos saat testing

def format_rupiah(amount: int) -> str:
    return f"Rp {amount:,}".replace(',', '.')

def hitung_diskon(harga_asli: int, harga_promo: int) -> int:
    if harga_asli <= 0:
        return 0
    return int(((harga_asli - harga_promo) / harga_asli) * 100)

async def update_user_activity(user_id: int, subscribe_status: bool = None):
    try:
        conn = sqlite3.connect('shopee_affiliate.db', check_same_thread=False)
        cursor = conn.cursor()
        if subscribe_status is not None:
            cursor.execute('''
                UPDATE pengguna 
                SET terakhir_aktif = CURRENT_TIMESTAMP, subscribe_channel = ?
                WHERE user_id = ?
            ''', (subscribe_status, user_id))
        else:
            cursor.execute('''
                UPDATE pengguna 
                SET terakhir_aktif = CURRENT_TIMESTAMP
                WHERE user_id = ?
            ''', (user_id,))
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"⚠️ Gagal update aktivitas user: {e}")

# ================= COMMANDS =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_id = update.effective_user.id
        username = update.effective_user.username or "Unknown"
        nama_depan = update.effective_user.first_name or "User"
        
        logger.info(f"👤 Start dari {user_id} ({username})")
        
        is_subscribed = await cek_subscribe_channel(user_id, context)
        
        conn = sqlite3.connect('shopee_affiliate.db', check_same_thread=False)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO pengguna (user_id, username, nama_depan, subscribe_channel)
            VALUES (?, ?, ?, ?)
        ''', (user_id, username, nama_depan, is_subscribed))
        conn.commit()
        conn.close()
        
        pesan = f"""
🛍️ **Selamat datang di Bot Promo Shopee!**

Halo {nama_depan}! Siap hunting promo terbaik hari ini? 🔥

📱 **Menu:**
• 🔥 Promo Hari Ini
• ⚡ Flash Sale
• 📦 Stok Terbatas

📢 Channel: {CHANNEL_USERNAME}
        """
        keyboard = [
            [InlineKeyboardButton("🔥 Promo Hari Ini", callback_data="promo_hari_ini")],
            [InlineKeyboardButton("📢 Channel Promo", url=f"https://t.me/{CHANNEL_USERNAME[1:]}")]
        ]
        await update.message.reply_text(
            pesan, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown'
        )
    except Exception as e:
        logger.error(f"❌ Error start: {e}")
        await update.message.reply_text("⚠️ Terjadi error, coba lagi.")

async def info_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
• /blast - Blast ke channel (Admin)
    """
    await update.message.reply_text(pesan, parse_mode='Markdown')

# Placeholder untuk command /promo
async def promo_hari_ini(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔥 Promo hari ini belum ada (dummy).")

# ================= ERROR HANDLER =================
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error(f"❌ Exception: {context.error}")

# ================= MAIN =================
def main():
    try:
        logger.info("🚀 Starting Bot...")

        # Force delete webhook
        try:
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/deleteWebhook"
            r = requests.post(url, json={"drop_pending_updates": True}, timeout=10)
            logger.info(f"Webhook delete: {r.text}")
            time.sleep(3)
        except Exception as e:
            logger.warning(f"⚠️ Gagal delete webhook: {e}")

        # Init bot class (buat DB)
        ShopeeAffiliateBot()

        # Build application
        application = Application.builder().token(BOT_TOKEN).build()
        application.add_error_handler(error_handler)

        # Commands
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("info", info_command))
        application.add_handler(CommandHandler("promo", promo_hari_ini))

        # Run polling
        logger.info("📡 Running polling...")
        application.run_polling(
            drop_pending_updates=True,
            allowed_updates=['message', 'callback_query'],
            poll_interval=2.0
        )

    except Exception as e:
        logger.error(f"💥 Fatal error: {e}")

if __name__ == "__main__":
    main()
