# Bot Shopee Affiliate dengan Channel Publik untuk Railway
# File: main.py

import os
import logging
import sqlite3
from datetime import datetime
from typing import Dict, List, Optional

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ChatMember
from telegram.ext import (
    Application, 
    CommandHandler, 
    CallbackQueryHandler, 
    MessageHandler,
    ContextTypes,
    filters
)
from telegram.error import TelegramError

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# TEMPORARY: Hardcoded configuration (ganti dengan env vars setelah Railway fixed)
HARDCODED_CONFIG = {
    'BOT_TOKEN': '8324792358:AAGXjXwm1U5cBs5c5Gd8VA3KVtYfxPVSPWA',
    'ADMIN_ID': 1239490619,
    'CHANNEL_ID': '@promoshopee22a', 
    'CHANNEL_USERNAME': '@promoshopee22a'
}

# Coba ambil dari environment variables dulu, jika tidak ada gunakan hardcoded
BOT_TOKEN = os.getenv('BOT_TOKEN') or HARDCODED_CONFIG['BOT_TOKEN']
ADMIN_ID = int(os.getenv('ADMIN_ID', str(HARDCODED_CONFIG['ADMIN_ID'])))
CHANNEL_ID = os.getenv('CHANNEL_ID') or HARDCODED_CONFIG['CHANNEL_ID']
CHANNEL_USERNAME = os.getenv('CHANNEL_USERNAME') or HARDCODED_CONFIG['CHANNEL_USERNAME']

logger.info(f"🔧 Using BOT_TOKEN: {BOT_TOKEN[:20]}...")
logger.info(f"🔧 Using ADMIN_ID: {ADMIN_ID}")
logger.info(f"🔧 Using CHANNEL_ID: {CHANNEL_ID}")
logger.info(f"🔧 Using CHANNEL_USERNAME: {CHANNEL_USERNAME}")

class ShopeeAffiliateBot:
    def __init__(self):
        self.init_database()
    
    def init_database(self):
        """Inisialisasi database SQLite"""
        try:
            conn = sqlite3.connect('shopee_affiliate.db', check_same_thread=False)
            cursor = conn.cursor()
            
            # Tabel produk
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
            
            # Tabel pengguna bot
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
            
            # Tabel preferensi pengguna
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS preferensi_user (
                    user_id INTEGER,
                    kategori TEXT,
                    min_diskon INTEGER DEFAULT 10,
                    max_harga INTEGER,
                    notifikasi_flash_sale BOOLEAN DEFAULT 1,
                    PRIMARY KEY (user_id, kategori)
                )
            ''')
            
            conn.commit()
            conn.close()
            logger.info("✅ Database berhasil diinisialisasi")
            
        except Exception as e:
            logger.error(f"❌ Error inisialisasi database: {e}")
            raise e

# === FUNGSI HELPER ===

async def cek_subscribe_channel(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Cek apakah user sudah subscribe channel"""
    try:
        member = await context.bot.get_chat_member(CHANNEL_ID, user_id)
        return member.status in [ChatMember.MEMBER, ChatMember.ADMINISTRATOR, ChatMember.OWNER]
    except Exception as e:
        logger.warning(f"Error checking channel subscription for user {user_id}: {e}")
        # Return True untuk testing jika channel belum siap
        return True

def format_rupiah(amount: int) -> str:
    """Format angka ke format rupiah"""
    return f"Rp {amount:,}".replace(',', '.')

def hitung_diskon(harga_asli: int, harga_promo: int) -> int:
    """Hitung persentase diskon"""
    if harga_asli <= 0:
        return 0
    return int(((harga_asli - harga_promo) / harga_asli) * 100)

async def update_user_activity(user_id: int, subscribe_status: bool = None):
    """Update aktivitas user di database"""
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
        logger.error(f"Error updating user activity: {e}")

# === COMMAND HANDLERS ===

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler untuk command /start"""
    try:
        user_id = update.effective_user.id
        username = update.effective_user.username or "Unknown"
        nama_depan = update.effective_user.first_name or "User"
        
        logger.info(f"User {user_id} ({username}) started the bot")
        
        # Cek status subscribe channel
        is_subscribed = await cek_subscribe_channel(user_id, context)
        
        # Simpan atau update user di database
        conn = sqlite3.connect('shopee_affiliate.db', check_same_thread=False)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO pengguna (user_id, username, nama_depan, subscribe_channel)
            VALUES (?, ?, ?, ?)
        ''', (user_id, username, nama_depan, is_subscribed))
        conn.commit()
        conn.close()
        
        # Debug info untuk admin
        if user_id == ADMIN_ID:
            debug_info = f"""
🔧 **DEBUG INFO (Admin Only)**
🆔 Your User ID: `{user_id}`
📱 Username: @{username}
👤 Name: {nama_depan}
📢 Channel: {CHANNEL_ID}
✅ Subscribed: {is_subscribed}
🤖 Bot Status: ✅ ONLINE

---
            """
        else:
            debug_info = ""
        
        pesan_welcome = f"""
{debug_info}🛍️ **Selamat datang di Bot Promo Shopee!**

Hai {nama_depan}! Siap hunting promo terbaik hari ini? 🔥

📱 **Menu Utama:**
• `/promo` - Promo terbaru hari ini
• `/tambah` - Tambah produk (Admin only)
• `/info` - Info bot

🔔 **Bot Status:** ✅ ONLINE

Ketik `/promo` untuk mulai belanja hemat! 🛒
        """
        
        keyboard = [
            [InlineKeyboardButton("🔥 Promo Hari Ini", callback_data="promo_hari_ini")],
            [InlineKeyboardButton("📢 Channel Promo", url=f"https://t.me/{CHANNEL_USERNAME[1:]}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            pesan_welcome, 
            reply_markup=reply_markup, 
            parse_mode='Markdown'
        )
        
    except Exception as e:
        logger.error(f"Error in start command: {e}")
        await update.message.reply_text(
            f"❌ Terjadi error: {str(e)}"
        )

async def info_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Info tentang bot"""
    try:
        pesan_info = f"""
🤖 **Bot Shopee Affiliate Info**

📊 **Status:** ✅ ONLINE
🆔 **Bot Token:** {BOT_TOKEN[:20]}...
👤 **Admin ID:** {ADMIN_ID}
📢 **Channel:** {CHANNEL_USERNAME}

🔧 **Available Commands:**
• `/start` - Mulai bot
• `/promo` - Lihat promo
• `/info` - Info bot
• `/tambah` - Tambah produk (Admin only)

📅 **Build:** September 2025
        """
        
        await update.message.reply_text(pesan_info, parse_mode='Markdown')
    except Exception as e:
        logger.error(f"Error in info command: {e}")
        await update.message.reply_text("❌ Terjadi error saat menampilkan info.")

async def promo_hari_ini(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler untuk command /promo"""
    try:
        conn = sqlite3.connect('shopee_affiliate.db', check_same_thread=False)
        cursor = conn.cursor()
        
        # Ambil promo aktif hari ini
        cursor.execute('''
            SELECT nama, harga_asli, harga_promo, diskon_persen, 
                   link_affiliate, deskripsi, stok_terbatas
            FROM produk 
            WHERE aktif = 1 
            ORDER BY diskon_persen DESC 
            LIMIT 8
        ''')
        
        produk_list = cursor.fetchall()
        conn.close()
        
        if not produk_list:
            await update.message.reply_text(
                "🤔 **Belum ada promo hari ini.**\n\n"
                "Admin sedang update promo terbaru! \n"
                "Gunakan `/tambah` untuk menambah produk (admin only)",
                parse_mode='Markdown'
            )
            return
        
        pesan = "🔥 **PROMO SHOPEE HARI INI** 🔥\n\n"
        pesan += f"📅 *{datetime.now().strftime('%d %B %Y')}*\n\n"
        
        for i, (nama, harga_asli, harga_promo, diskon, link, desc, stok_terbatas) in enumerate(produk_list, 1):
            harga_asli_format = format_rupiah(harga_asli)
            harga_promo_format = format_rupiah(harga_promo)
            hemat = format_rupiah(harga_asli - harga_promo)
            
            pesan += f"**{i}. {nama}**\n"
            pesan += f"💰 ~~{harga_asli_format}~~ → **{harga_promo_format}**\n"
            pesan += f"🏷️ Hemat {diskon}% ({hemat})\n"
            
            if stok_terbatas:
                pesan += f"⚠️ *Stok terbatas!*\n"
            
            if desc:
                pesan += f"📝 {desc}\n"
            
            pesan += f"[🛒 BELI SEKARANG]({link})\n\n"
        
        pesan += f"📢 **Channel:** {CHANNEL_USERNAME}"
        
        await update.message.reply_text(
            pesan, 
            parse_mode='Markdown', 
            disable_web_page_preview=True
        )
        
    except Exception as e:
        logger.error(f"Error in promo_hari_ini: {e}")
        await update.message.reply_text("❌ Terjadi error saat mengambil data promo.")

# === ADMIN COMMANDS ===

async def tambah_produk(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Command admin untuk menambah produk"""
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Command ini hanya untuk admin!")
        return
    
    if not context.args:
        contoh_format = """
📝 **Format Tambah Produk:**

`/tambah iPhone 15 Pro | Elektronik | 15999000 | 12999000 | https://shopee.co.id/xxx?af_siteid=123 | Garansi resmi iBox 1 tahun | 1 | 1`

**Keterangan:**
1. Nama Produk
2. Kategori  
3. Harga Asli
4. Harga Promo
5. Link Affiliate
6. Deskripsi
7. Stok Terbatas (0/1)
8. Flash Sale (0/1)

**Pisahkan dengan tanda | (pipe)**
        """
        await update.message.reply_text(contoh_format, parse_mode='Markdown')
        return
    
    try:
        data_produk = ' '.join(context.args).split('|')
        
        if len(data_produk) < 6:
            raise ValueError("Data tidak lengkap! Minimal 6 kolom.")
        
        nama = data_produk[0].strip()
        kategori = data_produk[1].strip()
        harga_asli = int(data_produk[2].strip())
        harga_promo = int(data_produk[3].strip())
        link_affiliate = data_produk[4].strip()
        deskripsi = data_produk[5].strip()
        stok_terbatas = bool(int(data_produk[6].strip())) if len(data_produk) > 6 else False
        flash_sale = bool(int(data_produk[7].strip())) if len(data_produk) > 7 else False
        
        # Hitung diskon
        diskon_persen = hitung_diskon(harga_asli, harga_promo)
        
        # Simpan ke database
        conn = sqlite3.connect('shopee_affiliate.db', check_same_thread=False)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO produk (nama, kategori, harga_asli, harga_promo, 
                              diskon_persen, link_affiliate, deskripsi, 
                              stok_terbatas, flash_sale)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (nama, kategori, harga_asli, harga_promo, diskon_persen, 
              link_affiliate, deskripsi, stok_terbatas, flash_sale))
        
        produk_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        # Konfirmasi berhasil
        harga_asli_format = format_rupiah(harga_asli)
        harga_promo_format = format_rupiah(harga_promo)
        
        pesan_sukses = f"""
✅ **Produk berhasil ditambahkan!**

🆔 **ID:** {produk_id}
📱 **Nama:** {nama}
🏷️ **Kategori:** {kategori}
💰 **Harga:** ~~{harga_asli_format}~~ → **{harga_promo_format}**
🔥 **Diskon:** {diskon_persen}%
⚡ **Flash Sale:** {'Ya' if flash_sale else 'Tidak'}
⚠️ **Stok Terbatas:** {'Ya' if stok_terbatas else 'Tidak'}

Gunakan `/promo` untuk melihat semua produk.
        """
        
        await update.message.reply_text(pesan_sukses, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in tambah_produk: {e}")
        await update.message.reply_text(
            f"❌ **Error:** {str(e)}\n\n"
            "Periksa format input! Gunakan `/tambah` tanpa parameter untuk melihat contoh.",
            parse_mode='Markdown'
        )

# === CALLBACK HANDLERS ===

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler untuk inline keyboard callbacks"""
    query = update.callback_query
    await query.answer()
    
    try:
        if query.data == "promo_hari_ini":
            # Redirect ke function promo_hari_ini
            # Update the update object to use query.message
            new_update = Update(
                update_id=update.update_id,
                message=query.message,
                callback_query=None
            )
            await promo_hari_ini(new_update, context)
        
    except Exception as e:
        logger.error(f"Error in callback_handler: {e}")
        await query.message.reply_text("❌ Terjadi error. Silakan coba lagi.")

# === MESSAGE HANDLER ===
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle semua pesan text yang tidak match dengan commands"""
    try:
        # Cek apakah update dan objek yang diperlukan ada
        if not update or not update.effective_user or not update.message:
            logger.warning("Update object is incomplete")
            return
            
        user_id = update.effective_user.id
        message_text = update.message.text
        
        # Cek apakah message_text ada
        if not message_text:
            return
            
        message_text = message_text.lower()
        
        # Update user activity
        await update_user_activity(user_id)
        
        # Auto-reply untuk pesan umum
        if any(word in message_text for word in ['halo', 'hai', 'hello', 'hi']):
            await update.message.reply_text(
                "👋 Halo! Selamat datang di Bot Promo Shopee!\n\n"
                "Ketik /start untuk melihat menu utama atau\n"
                "Ketik /promo untuk melihat promo hari ini! 🛒"
            )
        elif any(word in message_text for word in ['promo', 'diskon', 'murah']):
            await update.message.reply_text(
                "🔥 Mau lihat promo terbaru? Ketik /promo ya!\n\n"
                "Ada banyak produk dengan diskon gila-gilaan! 🛍️"
            )
        elif any(word in message_text for word in ['help', 'bantuan']):
            await update.message.reply_text(
                "🤖 **Bantuan Bot Shopee**\n\n"
                "**Commands yang tersedia:**\n"
                "• /start - Menu utama\n"
                "• /promo - Lihat promo hari ini\n"
                "• /info - Info tentang bot\n\n"
                "Butuh bantuan lain? Chat admin ya! 😊",
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text(
                "🤔 Maaf, saya tidak mengerti pesan Anda.\n\n"
                "Coba ketik /start untuk melihat menu atau\n"
                "/promo untuk melihat promo terbaru! 🛒"
            )
            
    except Exception as e:
        logger.error(f"Error in handle_message: {e}")
        # Cek apakah update.message masih ada sebelum mencoba reply
        if update and update.message:
            try:
                await update.message.reply_text(
                    "❌ Terjadi error. Silakan coba lagi atau gunakan /start"
                )
            except:
                # Jika reply gagal, log saja
                logger.error("Failed to send error message to user")

# === ERROR HANDLER ===

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log the error"""
    logger.error(f"Exception while handling an update: {context.error}")
    
    # Jika ada update dan message, kirim error ke user
    if hasattr(update, 'message') and update.message:
        try:
            await update.message.reply_text(
                "❌ Terjadi kesalahan sistem. Silakan coba lagi dalam beberapa saat."
            )
        except:
            pass

def main():
    """Main function untuk menjalankan bot"""
    try:
        logger.info("🚀 Starting Shopee Affiliate Bot...")
        
        # Initialize bot
        bot = ShopeeAffiliateBot()
        logger.info("✅ Bot class initialized")
        
        # Create application
        logger.info("🔧 Building Telegram application...")
        application = Application.builder().token(BOT_TOKEN).build()
        logger.info("✅ Telegram application built successfully")
        
        # Add error handler
        application.add_error_handler(error_handler)
        
        # User Commands
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("promo", promo_hari_ini))
        application.add_handler(CommandHandler("info", info_command))
        
        # Admin Commands
        application.add_handler(CommandHandler("tambah", tambah_produk))
        
        # Callback handlers
        application.add_handler(CallbackQueryHandler(callback_handler))
        
        # Photo handler untuk gambar produk
        application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
        
        # Message handler untuk handle semua text messages
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        
        logger.info("✅ All handlers registered")
        
        # Start bot
        port = int(os.environ.get('PORT', 8080))
        app_name = os.environ.get('RAILWAY_STATIC_URL')
        
        logger.info(f"🌐 Port: {port}")
        logger.info(f"🌐 App URL: {app_name}")
        
        # Always use polling for now (simpler and more reliable)
        logger.info("🔄 Starting polling mode")
        application.run_polling(drop_pending_updates=True)
            
    except Exception as e:
        logger.error(f"💥 Critical error starting bot: {e}")
        raise e

if __name__ == '__main__':
    main()