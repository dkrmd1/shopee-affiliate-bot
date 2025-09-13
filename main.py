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

# Setup logging DULU sebelum yang lain
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Debug environment variables
logger.info("🔍 Checking environment variables...")
for key in ['BOT_TOKEN', 'ADMIN_ID', 'CHANNEL_ID', 'CHANNEL_USERNAME', 'PORT']:
    value = os.getenv(key)
    if key == 'BOT_TOKEN' and value:
        logger.info(f"✅ {key}: {value[:20]}..." if value else f"❌ {key}: Not set")
    else:
        logger.info(f"✅ {key}: {value}" if value else f"❌ {key}: Not set")

# Konfigurasi Environment Variables dengan validasi
BOT_TOKEN = os.getenv('BOT_TOKEN')
ADMIN_ID_STR = os.getenv('ADMIN_ID', '0')
CHANNEL_ID = os.getenv('CHANNEL_ID')
CHANNEL_USERNAME = os.getenv('CHANNEL_USERNAME', '@promoshopee22a')

# Validasi environment variables
if not BOT_TOKEN:
    logger.error("❌ BOT_TOKEN tidak ditemukan dalam environment variables!")
    exit(1)

if BOT_TOKEN == "your_bot_token_here" or len(BOT_TOKEN) < 40:
    logger.error("❌ BOT_TOKEN tidak valid! Pastikan token dari BotFather sudah benar.")
    exit(1)

try:
    ADMIN_ID = int(ADMIN_ID_STR)
    if ADMIN_ID == 0:
        logger.warning("⚠️ ADMIN_ID tidak diset, gunakan /start untuk mendapatkan user_id Anda")
except ValueError:
    logger.error("❌ ADMIN_ID harus berupa angka!")
    exit(1)

if not CHANNEL_ID:
    logger.error("❌ CHANNEL_ID tidak ditemukan! Format: @channelname atau -100xxxxxxxxx")
    exit(1)

logger.info(f"✅ Bot Token: {BOT_TOKEN[:20]}...")
logger.info(f"✅ Admin ID: {ADMIN_ID}")
logger.info(f"✅ Channel ID: {CHANNEL_ID}")
logger.info(f"✅ Channel Username: {CHANNEL_USERNAME}")

class ShopeeAffiliateBot:
    def __init__(self):
        self.init_database()
    
    def init_database(self):
        """Inisialisasi database SQLite"""
        try:
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
            logger.info("✅ Database berhasil diinisialisasi")
            
        except Exception as e:
            logger.error(f"❌ Error inisialisasi database: {e}")
            exit(1)

# === FUNGSI HELPER ===

async def cek_subscribe_channel(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Cek apakah user sudah subscribe channel"""
    try:
        member = await context.bot.get_chat_member(CHANNEL_ID, user_id)
        return member.status in [ChatMember.MEMBER, ChatMember.ADMINISTRATOR, ChatMember.OWNER]
    except Exception as e:
        logger.warning(f"Error checking channel subscription for user {user_id}: {e}")
        return False

def format_rupiah(amount: int) -> str:
    """Format angka ke format rupiah"""
    return f"Rp {amount:,}".replace(',', '.')

def hitung_diskon(harga_asli: int, harga_promo: int) -> int:
    """Hitung persentase diskon"""
    return int(((harga_asli - harga_promo) / harga_asli) * 100)

async def update_user_activity(user_id: int, subscribe_status: bool = None):
    """Update aktivitas user di database"""
    try:
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
    except Exception as e:
        logger.error(f"Error updating user activity: {e}")

# === COMMAND HANDLERS ===

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler untuk command /start"""
    try:
        user_id = update.effective_user.id
        username = update.effective_user.username
        nama_depan = update.effective_user.first_name
        
        logger.info(f"User {user_id} ({username}) started the bot")
        
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
        
        # Debug info untuk admin
        if user_id == ADMIN_ID:
            debug_info = f"""
🔧 **DEBUG INFO (Admin Only)**
🆔 Your User ID: `{user_id}`
📱 Username: @{username}
👤 Name: {nama_depan}
📢 Channel: {CHANNEL_ID}
✅ Subscribed: {is_subscribed}

---
            """
        else:
            debug_info = ""
        
        if not is_subscribed:
            # Jika belum subscribe, minta subscribe dulu
            pesan_subscribe = f"""
{debug_info}🛍️ **Selamat datang di Bot Promo Shopee!**

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
{debug_info}🛍️ **Selamat datang di Bot Promo Shopee!**

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
        
    except Exception as e:
        logger.error(f"Error in start command: {e}")
        await update.message.reply_text(
            f"❌ Terjadi error saat memulai bot. Silakan coba lagi atau hubungi admin."
        )

async def promo_hari_ini(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler untuk command /promo"""
    try:
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
        
    except Exception as e:
        logger.error(f"Error in promo_hari_ini: {e}")
        await update.message.reply_text("❌ Terjadi error saat mengambil data promo.")

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
        logger.error(f"Error in tambah_produk: {e}")
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

👥 *Join bot untuk promo lainnya:* @Promosi_shopeeBot
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
        logger.error(f"Error in kirim_ke_channel: {e}")
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
        logger.error(f"Error in broadcast_produk: {e}")
        await update.message.reply_text(f"❌ Error: {str(e)}")

# === CALLBACK HANDLERS ===

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler untuk inline keyboard callbacks"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    
    try:
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
        
    except Exception as e:
        logger.error(f"Error in callback_handler: {e}")
        await query.message.reply_text("❌ Terjadi error. Silakan coba lagi.")

# === ERROR HANDLER ===

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log the error and send a telegram message to notify the developer."""
    logger.error(f"Exception while handling an update: {context.error}")
    
    # Send message to admin if error occurs
    if ADMIN_ID != 0:
        try:
            error_message = f"""
❌ **Bot Error Report**

🕐 Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
🔍 Error: `{str(context.error)[:1000]}`
👤 Update: {update}

Please check the logs for more details.
            """
            await context.bot.send_message(
                chat_id=ADMIN_ID,
                text=error_message,
                parse_mode='Markdown'
            )
        except Exception as e:
            logger.error(f"Failed to send error message to admin: {e}")

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
        
        # Admin Commands
        application.add_handler(CommandHandler("tambah", tambah_produk))
        application.add_handler(CommandHandler("kirim_channel", kirim_ke_channel))
        application.add_handler(CommandHandler("broadcast", broadcast_produk))
        
        # Callback handlers
        application.add_handler(CallbackQueryHandler(callback_handler))
        
        logger.info("✅ All handlers registered")
        
        # Start bot dengan webhook untuk Railway
        port = int(os.environ.get('PORT', 8080))
        app_name = os.environ.get('RAILWAY_STATIC_URL', 'localhost')
        
        logger.info(f"🌐 Port: {port}")
        logger.info(f"🌐 App URL: {app_name}")
        
        if app_name != 'localhost':
            # Production mode dengan webhook
            webhook_url = f"https://{app_name}/{BOT_TOKEN}"
            logger.info(f"🔗 Starting webhook mode at: {webhook_url}")
            
            application.run_webhook(
                listen="0.0.0.0",
                port=port,
                url_path=BOT_TOKEN,
                webhook_url=webhook_url
            )
        else:
            # Development mode dengan polling
            logger.info("🔄 Starting polling mode (development)")
            application.run_polling(drop_pending_updates=True)
            
    except Exception as e:
        logger.error(f"💥 Critical error starting bot: {e}")
        exit(1)

if __name__ == '__main__':
    main()