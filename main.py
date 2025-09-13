# Bot Shopee Affiliate dengan Channel Publik untuk Railway
# File: main.py

import os
import logging
import asyncio
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import json

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

# Konfigurasi Environment Variables
BOT_TOKEN = os.getenv('BOT_TOKEN')
ADMIN_ID = int(os.getenv('ADMIN_ID', '0'))  # ID Telegram Admin
CHANNEL_ID = os.getenv('CHANNEL_ID')  # ID Channel publik (contoh: @promoshopee)
CHANNEL_USERNAME = os.getenv('CHANNEL_USERNAME', '@promoshopee')  # Username channel

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class ShopeeAffiliateBot:
    def __init__(self):
        self.init_database()
    
    def init_database(self):
        """Inisialisasi database SQLite"""
        conn = sqlite3.connect('shopee_affiliate.db')
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

# === FUNGSI HELPER ===

async def cek_subscribe_channel(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Cek apakah user sudah subscribe channel"""
    try:
        member = await context.bot.get_chat_member(CHANNEL_ID, user_id)
        return member.status in [ChatMember.MEMBER, ChatMember.ADMINISTRATOR, ChatMember.OWNER]
    except:
        return False

def format_rupiah(amount: int) -> str:
    """Format angka ke format rupiah"""
    return f"Rp {amount:,}".replace(',', '.')

def hitung_diskon(harga_asli: int, harga_promo: int) -> int:
    """Hitung persentase diskon"""
    return int(((harga_asli - harga_promo) / harga_asli) * 100)

async def update_user_activity(user_id: int, subscribe_status: bool = None):
    """Update aktivitas user di database"""
    conn = sqlite3.connect('shopee_affiliate.db')
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

# === COMMAND HANDLERS ===

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler untuk command /start"""
    user_id = update.effective_user.id
    username = update.effective_user.username
    nama_depan = update.effective_user.first_name
    
    # Cek status subscribe channel
    is_subscribed = await cek_subscribe_channel(user_id, context)
    
    # Simpan atau update user di database
    conn = sqlite3.connect('shopee_affiliate.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR REPLACE INTO pengguna (user_id, username, nama_depan, subscribe_channel)
        VALUES (?, ?, ?, ?)
    ''', (user_id, username, nama_depan, is_subscribed))
    conn.commit()
    conn.close()
    
    if not is_subscribed:
        # Jika belum subscribe, minta subscribe dulu
        pesan_subscribe = f"""
🛍️ **Selamat datang di Bot Promo Shopee!**

Hai {nama_depan}! Untuk mendapatkan akses penuh ke semua fitur bot, silakan **subscribe channel** kami dulu ya!

📢 **Channel:** {CHANNEL_USERNAME}
🎯 **Benefit subscribe:**
• Promo eksklusif setiap hari
• Flash sale alert real-time  
• Cashback & voucher gratis
• Update produk viral terbaru

👇 **Klik tombol di bawah untuk subscribe**
        """
        
        keyboard = [
            [InlineKeyboardButton("📢 Subscribe Channel", url=f"https://t.me/{CHANNEL_USERNAME[1:]}")],
            [InlineKeyboardButton("✅ Sudah Subscribe", callback_data="check_subscribe")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            pesan_subscribe, 
            reply_markup=reply_markup, 
            parse_mode='Markdown'
        )
        return
    
    # Jika sudah subscribe, tampilkan menu utama
    pesan_welcome = f"""
🛍️ **Selamat datang di Bot Promo Shopee!**

Hai {nama_depan}! Siap hunting promo terbaik hari ini? 🔥

📱 **Menu Utama:**
• `/promo` - Promo terbaru hari ini
• `/flashsale` - Flash sale yang sedang berlangsung
• `/kategori` - Pilih kategori favorit
• `/voucher` - Kode voucher gratis
• `/pengaturan` - Atur notifikasi & preferensi

🔔 **Notifikasi Otomatis:**
• Promo harian jam 08.00 & 20.00
• Flash sale alert real-time

Ketik `/promo` untuk mulai belanja hemat! 🛒
            """
            
            keyboard = [
                [InlineKeyboardButton("🔥 Promo Hari Ini", callback_data="promo_hari_ini")],
                [InlineKeyboardButton("⚡ Flash Sale", callback_data="flash_sale_aktif")],
                [InlineKeyboardButton("📢 Channel Promo", url=f"https://t.me/{CHANNEL_USERNAME[1:]}")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                pesan_welcome,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
        else:
            await query.edit_message_text(
                f"❌ **Kamu belum subscribe channel kami.**\n\n"
                f"Silakan subscribe dulu: {CHANNEL_USERNAME}\n"
                f"Kemudian klik tombol '✅ Sudah Subscribe' lagi.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("📢 Subscribe Channel", url=f"https://t.me/{CHANNEL_USERNAME[1:]}")],
                    [InlineKeyboardButton("✅ Sudah Subscribe", callback_data="check_subscribe")]
                ]),
                parse_mode='Markdown'
            )
    
    elif query.data == "promo_hari_ini":
        # Redirect ke function promo_hari_ini
        update.message = query.message
        await promo_hari_ini(update, context)
    
    elif query.data == "flash_sale_aktif":
        update.message = query.message
        await flash_sale_aktif(update, context)
    
    elif query.data == "pilih_kategori":
        if not await cek_subscribe_channel(user_id, context):
            await query.edit_message_text(
                f"🔒 Fitur ini hanya untuk subscriber channel.\n\nSubscribe dulu: {CHANNEL_USERNAME}",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("📢 Subscribe", url=f"https://t.me/{CHANNEL_USERNAME[1:]}")],
                    [InlineKeyboardButton("✅ Sudah Subscribe", callback_data="check_subscribe")]
                ])
            )
            return
        
        keyboard = [
            [InlineKeyboardButton("📱 Elektronik", callback_data="kat_elektronik")],
            [InlineKeyboardButton("👕 Fashion Pria", callback_data="kat_fashion_pria")],
            [InlineKeyboardButton("👗 Fashion Wanita", callback_data="kat_fashion_wanita")],
            [InlineKeyboardButton("🏠 Rumah Tangga", callback_data="kat_rumah_tangga")],
            [InlineKeyboardButton("🎮 Gaming", callback_data="kat_gaming")],
            [InlineKeyboardButton("💄 Kecantikan", callback_data="kat_kecantikan")],
            [InlineKeyboardButton("🔙 Kembali", callback_data="menu_utama")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "🏷️ **Pilih Kategori Favorit:**\n\n"
            "Pilih kategori untuk mendapat promo yang sesuai dengan minatmu!\n"
            "Bot akan kirim notifikasi promo khusus kategori pilihanmu.",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    elif query.data.startswith("kat_"):
        # Handle kategori selection
        kategori = query.data.replace("kat_", "").replace("_", " ").title()
        
        # Simpan preferensi kategori user
        conn = sqlite3.connect('shopee_affiliate.db')
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO preferensi_user (user_id, kategori)
            VALUES (?, ?)
        ''', (user_id, kategori))
        conn.commit()
        
        # Ambil produk dari kategori tersebut
        cursor.execute('''
            SELECT nama, harga_asli, harga_promo, diskon_persen, link_affiliate
            FROM produk 
            WHERE aktif = 1 AND LOWER(kategori) LIKE LOWER(?)
            ORDER BY diskon_persen DESC 
            LIMIT 5
        ''', (f"%{kategori}%",))
        
        produk_kategori = cursor.fetchall()
        conn.close()
        
        if produk_kategori:
            pesan = f"✅ **Kategori {kategori} berhasil dipilih!**\n\n"
            pesan += f"🔥 **Promo {kategori} Terbaik:**\n\n"
            
            for nama, harga_asli, harga_promo, diskon, link in produk_kategori:
                harga_asli_format = format_rupiah(harga_asli)
                harga_promo_format = format_rupiah(harga_promo)
                
                pesan += f"📱 **{nama}**\n"
                pesan += f"💰 ~~{harga_asli_format}~~ → **{harga_promo_format}** ({diskon}%)\n"
                pesan += f"[🛒 BELI]({link})\n\n"
            
            pesan += f"🔔 Kamu akan mendapat notifikasi khusus promo {kategori}!"
        else:
            pesan = f"✅ **Kategori {kategori} berhasil dipilih!**\n\n"
            pesan += f"🔔 Kamu akan mendapat notifikasi khusus untuk kategori {kategori}.\n\n"
            pesan += "Saat ini belum ada promo untuk kategori ini, tapi nanti akan ada notifikasi otomatis!"
        
        keyboard = [
            [InlineKeyboardButton("🔙 Pilih Kategori Lain", callback_data="pilih_kategori")],
            [InlineKeyboardButton("🏠 Menu Utama", callback_data="menu_utama")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            pesan,
            reply_markup=reply_markup,
            parse_mode='Markdown',
            disable_web_page_preview=True
        )
    
    elif query.data == "aktifkan_notif":
        # Aktifkan notifikasi user
        conn = sqlite3.connect('shopee_affiliate.db')
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE pengguna SET notifikasi_aktif = 1 WHERE user_id = ?
        ''', (user_id,))
        conn.commit()
        conn.close()
        
        await query.edit_message_text(
            "✅ **Notifikasi berhasil diaktifkan!**\n\n"
            "🔔 Kamu akan mendapat:\n"
            "• Flash sale alert real-time\n"
            "• Promo harian jam 8 pagi & 8 malam\n"
            "• Weekend special deals\n"
            "• Voucher gratis notification\n\n"
            f"📢 **Jangan lupa juga follow channel:** {CHANNEL_USERNAME}",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🏠 Menu Utama", callback_data="menu_utama")],
                [InlineKeyboardButton("📢 Channel", url=f"https://t.me/{CHANNEL_USERNAME[1:]}")]
            ]),
            parse_mode='Markdown'
        )
    
    elif query.data == "menu_utama":
        # Kembali ke menu utama
        pesan_menu = f"""
🛍️ **Bot Promo Shopee**

📱 **Menu Utama:**
• `/promo` - Promo terbaru hari ini
• `/flashsale` - Flash sale yang sedang berlangsung
• `/kategori` - Pilih kategori favorit
• `/voucher` - Kode voucher gratis
• `/pengaturan` - Atur notifikasi & preferensi

🔔 **Notifikasi Otomatis:**
• Promo harian jam 08.00 & 20.00
• Flash sale alert real-time
• Weekend special deals

Ketik `/promo` untuk mulai belanja hemat! 🛒
        """
        
        keyboard = [
            [InlineKeyboardButton("🔥 Promo Hari Ini", callback_data="promo_hari_ini")],
            [InlineKeyboardButton("⚡ Flash Sale", callback_data="flash_sale_aktif")],
            [InlineKeyboardButton("🏷️ Kategori", callback_data="pilih_kategori")],
            [InlineKeyboardButton("📢 Channel Promo", url=f"https://t.me/{CHANNEL_USERNAME[1:]}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            pesan_menu,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

# === SCHEDULED JOBS ===

async def broadcast_harian_pagi(context: ContextTypes.DEFAULT_TYPE):
    """Broadcast promo harian pagi jam 8"""
    conn = sqlite3.connect('shopee_affiliate.db')
    cursor = conn.cursor()
    
    # Ambil top 5 promo hari ini
    cursor.execute('''
        SELECT nama, harga_asli, harga_promo, diskon_persen, link_affiliate
        FROM produk 
        WHERE aktif = 1 AND flash_sale = 0
        ORDER BY diskon_persen DESC 
        LIMIT 5
    ''')
    
    produk_list = cursor.fetchall()
    
    # Kirim ke channel dulu
    if produk_list:
        pesan_channel = "🌅 **SELAMAT PAGI! PROMO TERBAIK HARI INI** 🌅\n\n"
        pesan_channel += f"📅 *{datetime.now().strftime('%d %B %Y')}*\n\n"
        
        for i, (nama, harga_asli, harga_promo, diskon, link) in enumerate(produk_list, 1):
            harga_asli_format = format_rupiah(harga_asli)
            harga_promo_format = format_rupiah(harga_promo)
            hemat = format_rupiah(harga_asli - harga_promo)
            
            pesan_channel += f"**{i}. {nama}**\n"
            pesan_channel += f"💰 ~~{harga_asli_format}~~ → **{harga_promo_format}**\n"
            pesan_channel += f"🏷️ Hemat {diskon}% ({hemat})\n"
            pesan_channel += f"[🛒 BELI SEKARANG]({link})\n\n"
        
        pesan_channel += f"👥 *Join bot untuk notifikasi promo:* @{BOT_TOKEN.split(':')[0]}\n"
        pesan_channel += "⏰ *Update lagi jam 8 malam!*"
        
        # Kirim ke channel
        try:
            await context.bot.send_message(
                chat_id=CHANNEL_ID,
                text=pesan_channel,
                parse_mode='Markdown',
                disable_web_page_preview=True
            )
        except Exception as e:
            logger.error(f"Error kirim ke channel: {e}")
    
    # Broadcast ke user bot yang aktif notifikasi
    cursor.execute('''
        SELECT user_id FROM pengguna 
        WHERE subscribe_channel = 1 AND notifikasi_aktif = 1
    ''')
    users = cursor.fetchall()
    conn.close()
    
    if not produk_list or not users:
        return
    
    # Format pesan untuk user bot
    pesan_bot = "🌅 **SELAMAT PAGI! PROMO PILIHAN HARI INI** 🌅\n\n"
    
    for i, (nama, harga_asli, harga_promo, diskon, link) in enumerate(produk_list, 1):
        harga_asli_format = format_rupiah(harga_asli)
        harga_promo_format = format_rupiah(harga_promo)
        
        pesan_bot += f"**{i}. {nama}**\n"
        pesan_bot += f"💰 ~~{harga_asli_format}~~ → **{harga_promo_format}** ({diskon}% OFF)\n"
        pesan_bot += f"[🛒 BELI]({link})\n\n"
    
    pesan_bot += f"📢 **Lihat promo lengkap:** {CHANNEL_USERNAME}\n"
    pesan_bot += "⏰ *Update lagi jam 8 malam!*"
    
    # Broadcast ke user dengan rate limiting
    for (user_id,) in users:
        try:
            await context.bot.send_message(
                chat_id=user_id,
                text=pesan_bot,
                parse_mode='Markdown',
                disable_web_page_preview=True
            )
            await asyncio.sleep(0.05)
        except:
            continue

async def broadcast_harian_malam(context: ContextTypes.DEFAULT_TYPE):
    """Broadcast promo malam jam 8"""
    conn = sqlite3.connect('shopee_affiliate.db')
    cursor = conn.cursor()
    
    # Ambil produk flash sale atau promo spesial malam
    cursor.execute('''
        SELECT nama, harga_asli, harga_promo, diskon_persen, link_affiliate, flash_sale
        FROM produk 
        WHERE aktif = 1 
        ORDER BY flash_sale DESC, diskon_persen DESC 
        LIMIT 5
    ''')
    
    produk_list = cursor.fetchall()
    
    # Kirim ke channel
    if produk_list:
        pesan_channel = "🌃 **PROMO MALAM HARI - WEEKEND DEALS** 🌃\n\n"
        
        for nama, harga_asli, harga_promo, diskon, link, flash_sale in produk_list:
            harga_asli_format = format_rupiah(harga_asli)
            harga_promo_format = format_rupiah(harga_promo)
            
            if flash_sale:
                pesan_channel += f"⚡ **FLASH SALE: {nama}**\n"
            else:
                pesan_channel += f"🔥 **{nama}**\n"
            
            pesan_channel += f"💰 ~~{harga_asli_format}~~ → **{harga_promo_format}** ({diskon}%)\n"
            pesan_channel += f"[🛒 BELI SEKARANG]({link})\n\n"
        
        pesan_channel += "🛌 *Selamat malam & happy shopping!*"
        
        try:
            await context.bot.send_message(
                chat_id=CHANNEL_ID,
                text=pesan_channel,
                parse_mode='Markdown',
                disable_web_page_preview=True
            )
        except Exception as e:
            logger.error(f"Error kirim ke channel: {e}")
    
    # Broadcast ke user
    cursor.execute('''
        SELECT user_id FROM pengguna 
        WHERE subscribe_channel = 1 AND notifikasi_aktif = 1
    ''')
    users = cursor.fetchall()
    conn.close()
    
    if not users:
        return
    
    pesan_bot = "🌃 **PROMO MALAM HARI** 🌃\n\n"
    pesan_bot += "Hay! Ada promo malam yang ga boleh dilewatin nih!\n\n"
    
    for nama, harga_asli, harga_promo, diskon, link, flash_sale in produk_list:
        harga_asli_format = format_rupiah(harga_asli)
        harga_promo_format = format_rupiah(harga_promo)
        
        if flash_sale:
            pesan_bot += f"⚡ **{nama}** (Flash Sale)\n"
        else:
            pesan_bot += f"🔥 **{nama}**\n"
        
        pesan_bot += f"💰 ~~{harga_asli_format}~~ → **{harga_promo_format}** ({diskon}%)\n"
        pesan_bot += f"[🛒 BELI]({link})\n\n"
    
    pesan_bot += "🛌 *Selamat malam & happy shopping!*"
    
    # Broadcast dengan rate limiting
    for (user_id,) in users:
        try:
            await context.bot.send_message(
                chat_id=user_id,
                text=pesan_bot,
                parse_mode='Markdown',
                disable_web_page_preview=True
            )
            await asyncio.sleep(0.05)
        except:
            continue

def main():
    """Main function untuk menjalankan bot"""
    # Initialize bot
    bot = ShopeeAffiliateBot()
    
    # Create application
    application = Application.builder().token(BOT_TOKEN).build()
    
    # User Commands
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("promo", promo_hari_ini))
    application.add_handler(CommandHandler("flashsale", flash_sale_aktif))
    
    # Admin Commands
    application.add_handler(CommandHandler("tambah", tambah_produk))
    application.add_handler(CommandHandler("lihat_produk", lihat_produk))
    application.add_handler(CommandHandler("kirim_channel", kirim_ke_channel))
    application.add_handler(CommandHandler("broadcast", broadcast_produk))
    
    # Callback handlers
    application.add_handler(CallbackQueryHandler(callback_handler))
    
    # Scheduled jobs
    job_queue = application.job_queue
    
    # Broadcast harian
    job_queue.run_daily(
        broadcast_harian_pagi, 
        time=datetime.strptime("08:00", "%H:%M").time(),
        name="broadcast_pagi"
    )
    job_queue.run_daily(
        broadcast_harian_malam, 
        time=datetime.strptime("20:00", "%H:%M").time(),
        name="broadcast_malam"
    )
    
    # Start bot dengan webhook untuk Railway
    port = int(os.environ.get('PORT', 8080))
    app_name = os.environ.get('RAILWAY_STATIC_URL', 'localhost')
    
    if app_name != 'localhost':
        # Production mode dengan webhook
        application.run_webhook(
            listen="0.0.0.0",
            port=port,
            url_path=BOT_TOKEN,
            webhook_url=f"https://{app_name}/{BOT_TOKEN}"
        )
    else:
        # Development mode dengan polling
        application.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    main().00 & 20.00
• Flash sale alert real-time
• Weekend special deals

Ketik `/promo` untuk mulai belanja hemat! 🛒
    """
    
    keyboard = [
        [InlineKeyboardButton("🔥 Promo Hari Ini", callback_data="promo_hari_ini")],
        [InlineKeyboardButton("⚡ Flash Sale", callback_data="flash_sale_aktif")],
        [InlineKeyboardButton("🏷️ Kategori", callback_data="pilih_kategori")],
        [InlineKeyboardButton("📢 Channel Promo", url=f"https://t.me/{CHANNEL_USERNAME[1:]}")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        pesan_welcome, 
        reply_markup=reply_markup, 
        parse_mode='Markdown'
    )

async def promo_hari_ini(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler untuk command /promo"""
    user_id = update.effective_user.id
    
    # Cek subscribe status
    if not await cek_subscribe_channel(user_id, context):
        await minta_subscribe(update, context)
        return
    
    await update_user_activity(user_id)
    
    conn = sqlite3.connect('shopee_affiliate.db')
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
            "Pantau terus channel kami untuk update terbaru 📢"
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
    
    pesan += f"📢 **Lihat lebih banyak promo di channel:** {CHANNEL_USERNAME}\n"
    pesan += "⏰ *Update setiap hari jam 8 pagi & 8 malam*"
    
    await update.message.reply_text(
        pesan, 
        parse_mode='Markdown', 
        disable_web_page_preview=True
    )

async def flash_sale_aktif(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler untuk flash sale"""
    user_id = update.effective_user.id
    
    if not await cek_subscribe_channel(user_id, context):
        await minta_subscribe(update, context)
        return
    
    await update_user_activity(user_id)
    
    conn = sqlite3.connect('shopee_affiliate.db')
    cursor = conn.cursor()
    
    # Ambil produk flash sale aktif
    cursor.execute('''
        SELECT nama, harga_asli, harga_promo, diskon_persen, 
               link_affiliate, deskripsi
        FROM produk 
        WHERE aktif = 1 AND flash_sale = 1
        ORDER BY diskon_persen DESC 
        LIMIT 6
    ''')
    
    flash_sale_list = cursor.fetchall()
    conn.close()
    
    if not flash_sale_list:
        pesan_kosong = f"""
⚡ **FLASH SALE SHOPEE** ⚡

🤔 Tidak ada flash sale saat ini.

🔔 **Aktifkan notifikasi** untuk mendapat alert flash sale:
• Flash sale biasanya dimulai jam 12.00, 18.00, dan 20.00
• Subscribe channel untuk update real-time

📢 **Channel:** {CHANNEL_USERNAME}
        """
        
        keyboard = [
            [InlineKeyboardButton("🔔 Aktifkan Notifikasi", callback_data="aktifkan_notif")],
            [InlineKeyboardButton("📢 Channel Promo", url=f"https://t.me/{CHANNEL_USERNAME[1:]}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            pesan_kosong,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        return
    
    pesan = "⚡ **FLASH SALE SHOPEE** ⚡\n\n"
    pesan += "🔥 *Promo terbatas waktu - Buruan sebelum kehabisan!*\n\n"
    
    for nama, harga_asli, harga_promo, diskon, link, desc in flash_sale_list:
        harga_asli_format = format_rupiah(harga_asli)
        harga_promo_format = format_rupiah(harga_promo)
        
        pesan += f"🔥 **{nama}**\n"
        pesan += f"💰 ~~{harga_asli_format}~~ → **{harga_promo_format}**\n"
        pesan += f"🏷️ **HEMAT {diskon}%**\n"
        pesan += f"[🛒 BELI SEKARANG]({link})\n\n"
    
    pesan += "⚠️ *Stock terbatas! Jangan sampai terlewat*\n"
    pesan += f"📢 **Update flash sale real-time:** {CHANNEL_USERNAME}"
    
    await update.message.reply_text(
        pesan, 
        parse_mode='Markdown', 
        disable_web_page_preview=True
    )

async def minta_subscribe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Minta user subscribe channel dulu"""
    pesan = f"""
🔒 **Akses Terbatas**

Maaf, fitur ini hanya untuk member yang sudah subscribe channel kami.

📢 **Subscribe dulu ya:** {CHANNEL_USERNAME}

🎯 **Keuntungan subscribe:**
• Promo eksklusif harian
• Flash sale alert real-time
• Voucher gratis
• Cashback notification

Setelah subscribe, klik "✅ Sudah Subscribe" di bawah.
    """
    
    keyboard = [
        [InlineKeyboardButton("📢 Subscribe Channel", url=f"https://t.me/{CHANNEL_USERNAME[1:]}")],
        [InlineKeyboardButton("✅ Sudah Subscribe", callback_data="check_subscribe")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        pesan,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

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
        
        # Validasi link affiliate
        if not ('shopee.co.id' in link_affiliate):
            raise ValueError("Link affiliate harus dari Shopee!")
        
        # Hitung diskon
        diskon_persen = hitung_diskon(harga_asli, harga_promo)
        
        # Simpan ke database
        conn = sqlite3.connect('shopee_affiliate.db')
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

**Command selanjutnya:**
• `/kirim_channel {produk_id}` - Kirim ke channel
• `/broadcast {produk_id}` - Broadcast ke semua user
• `/lihat_produk` - Lihat semua produk
        """
        
        await update.message.reply_text(pesan_sukses, parse_mode='Markdown')
        
    except Exception as e:
        await update.message.reply_text(
            f"❌ **Error:** {str(e)}\n\n"
            "Periksa format input! Gunakan `/tambah` tanpa parameter untuk melihat contoh."
        )

async def kirim_ke_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Kirim produk ke channel publik"""
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Command ini hanya untuk admin!")
        return
    
    if not context.args:
        await update.message.reply_text("Format: `/kirim_channel {produk_id}`")
        return
    
    try:
        produk_id = int(context.args[0])
        
        # Ambil data produk
        conn = sqlite3.connect('shopee_affiliate.db')
        cursor = conn.cursor()
        cursor.execute('''
            SELECT nama, harga_asli, harga_promo, diskon_persen, 
                   link_affiliate, deskripsi, stok_terbatas, flash_sale
            FROM produk WHERE id = ? AND aktif = 1
        ''', (produk_id,))
        
        produk = cursor.fetchone()
        conn.close()
        
        if not produk:
            await update.message.reply_text("❌ Produk tidak ditemukan atau tidak aktif!")
            return
        
        # Format pesan untuk channel
        nama, harga_asli, harga_promo, diskon, link, desc, stok_terbatas, flash_sale = produk
        harga_asli_format = format_rupiah(harga_asli)
        harga_promo_format = format_rupiah(harga_promo)
        hemat = format_rupiah(harga_asli - harga_promo)
        
        if flash_sale:
            pesan_channel = f"""
⚡ **FLASH SALE ALERT** ⚡

🔥 **{nama}**
💰 ~~{harga_asli_format}~~ → **{harga_promo_format}**
🏷️ **HEMAT {diskon}% ({hemat})**

{desc}

{'⚠️ *STOK TERBATAS!*' if stok_terbatas else ''}

[🛒 BELI SEKARANG]({link})

⏰ *Buruan sebelum kehabisan!*
            """
        else:
            pesan_channel = f"""
🛍️ **PROMO SHOPEE HARI INI** 🛍️

📱 **{nama}**
💰 ~~{harga_asli_format}~~ → **{harga_promo_format}**
🏷️ Hemat {diskon}% ({hemat})

📝 {desc}

{'⚠️ *Stok terbatas!*' if stok_terbatas else ''}

[🛒 BELI SEKARANG]({link})

👥 *Join bot untuk promo lainnya:* @{BOT_TOKEN.split(':')[0]}
            """
        
        # Kirim ke channel
        await context.bot.send_message(
            chat_id=CHANNEL_ID,
            text=pesan_channel,
            parse_mode='Markdown',
            disable_web_page_preview=True
        )
        
        await update.message.reply_text(
            f"✅ **Produk berhasil dikirim ke channel!**\n\n"
            f"📢 **Channel:** {CHANNEL_USERNAME}\n"
            f"📱 **Produk:** {nama}"
        )
        
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")

async def broadcast_produk(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Broadcast produk ke semua user bot"""
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Command ini hanya untuk admin!")
        return
    
    if not context.args:
        await update.message.reply_text("Format: `/broadcast {produk_id}`")
        return
    
    try:
        produk_id = int(context.args[0])
        
        # Ambil data produk
        conn = sqlite3.connect('shopee_affiliate.db')
        cursor = conn.cursor()
        cursor.execute('''
            SELECT nama, harga_asli, harga_promo, diskon_persen, link_affiliate, deskripsi
            FROM produk WHERE id = ? AND aktif = 1
        ''', (produk_id,))
        
        produk = cursor.fetchone()
        
        if not produk:
            await update.message.reply_text("❌ Produk tidak ditemukan!")
            return
        
        # Ambil semua user yang aktif dan subscribe channel
        cursor.execute('''
            SELECT user_id FROM pengguna 
            WHERE subscribe_channel = 1 AND notifikasi_aktif = 1
        ''')
        users = cursor.fetchall()
        conn.close()
        
        # Format pesan broadcast
        nama, harga_asli, harga_promo, diskon, link, desc = produk
        harga_asli_format = format_rupiah(harga_asli)
        harga_promo_format = format_rupiah(harga_promo)
        
        pesan_broadcast = f"""
🔥 **PROMO SPESIAL UNTUKMU!** 🔥

📱 **{nama}**
💰 ~~{harga_asli_format}~~ → **{harga_promo_format}**
🏷️ **HEMAT {diskon}%**

📝 {desc}

[🛒 BELI SEKARANG]({link})

⏰ *Jangan sampai terlewat ya!*

📢 *Lihat promo lainnya di channel:* {CHANNEL_USERNAME}
        """
        
        # Kirim broadcast dengan rate limiting
        berhasil = 0
        gagal = 0
        
        await update.message.reply_text("📤 Memulai broadcast...")
        
        for (user_id,) in users:
            try:
                await context.bot.send_message(
                    chat_id=user_id,
                    text=pesan_broadcast,
                    parse_mode='Markdown',
                    disable_web_page_preview=True
                )
                berhasil += 1
                await asyncio.sleep(0.05)  # Rate limiting
            except TelegramError:
                gagal += 1
        
        await update.message.reply_text(
            f"📢 **Broadcast selesai!**\n\n"
            f"✅ Berhasil: {berhasil} user\n"
            f"❌ Gagal: {gagal} user\n"
            f"📱 Produk: {nama}"
        )
        
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")

async def lihat_produk(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Lihat daftar semua produk - Admin only"""
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Command ini hanya untuk admin!")
        return
    
    conn = sqlite3.connect('shopee_affiliate.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id, nama, kategori, diskon_persen, aktif, flash_sale, stok_terbatas
        FROM produk 
        ORDER BY dibuat_pada DESC 
        LIMIT 15
    ''')
    
    produk_list = cursor.fetchall()
    conn.close()
    
    if not produk_list:
        await update.message.reply_text("📦 Belum ada produk yang ditambahkan.")
        return
    
    pesan = "📦 **DAFTAR PRODUK**\n\n"
    
    for pid, nama, kategori, diskon, aktif, flash_sale, stok_terbatas in produk_list:
        status_icon = "✅" if aktif else "❌"
        flash_icon = "⚡" if flash_sale else ""
        stok_icon = "⚠️" if stok_terbatas else ""
        
        pesan += f"{status_icon} **{pid}.** {nama} {flash_icon} {stok_icon}\n"
        pesan += f"🏷️ {kategori} | 🔥 {diskon}%\n\n"
    
    pesan += """
**Command untuk manage produk:**
• `/toggle {id}` - Aktif/nonaktif produk
• `/hapus {id}` - Hapus produk
• `/kirim_channel {id}` - Kirim ke channel
• `/broadcast {id}` - Broadcast ke user

**Legend:**
✅ Aktif | ❌ Nonaktif | ⚡ Flash Sale | ⚠️ Stok Terbatas
    """
    
    await update.message.reply_text(pesan, parse_mode='Markdown')

# === CALLBACK HANDLERS ===

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler untuk inline keyboard callbacks"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    
    if query.data == "check_subscribe":
        # Cek ulang status subscribe
        is_subscribed = await cek_subscribe_channel(user_id, context)
        
        if is_subscribed:
            # Update database
            conn = sqlite3.connect('shopee_affiliate.db')
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE pengguna SET subscribe_channel = 1 WHERE user_id = ?
            ''', (user_id,))
            conn.commit()
            conn.close()
            
            # Tampilkan menu utama
            pesan_welcome = f"""
✅ **Terima kasih sudah subscribe!**

🛍️ Selamat datang di Bot Promo Shopee!
Sekarang kamu bisa akses semua fitur bot.

📱 **Menu Utama:**
• `/promo` - Promo terbaru hari ini
• `/flashsale` - Flash sale yang sedang berlangsung
• `/kategori` - Pilih kategori favorit

🔔 **Notifikasi Otomatis:**
• Promo harian jam 08