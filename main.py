import logging
import os
import sqlite3
from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Update
)
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes
)

# =====================
# 🔧 Config
# =====================
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = os.getenv("ADMIN_ID")
CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME")

if not BOT_TOKEN:
    raise ValueError("❌ BOT_TOKEN belum di-set di Railway Variables!")

# =====================
# 🗂 Database Setup
# =====================
conn = sqlite3.connect("data.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
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
cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    kategori TEXT
)
""")
conn.commit()

# =====================
# 🚀 Start Command
# =====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if str(user_id) == str(ADMIN_ID):  # Admin Menu
        keyboard = [
            [InlineKeyboardButton("➕ Tambah Produk", callback_data="tambah_produk")],
            [InlineKeyboardButton("📋 Lihat Produk", callback_data="lihat_produk")],
            [InlineKeyboardButton("📢 Broadcast Produk", callback_data="broadcast")],
            [InlineKeyboardButton("📤 Kirim ke Channel", callback_data="kirim_channel")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("👑 Panel Admin", reply_markup=reply_markup)
    else:  # User Menu
        keyboard = [
            [InlineKeyboardButton("🛍️ Promo Hari Ini", callback_data="promo")],
            [InlineKeyboardButton("⚡ Flash Sale", callback_data="flashsale")],
            [InlineKeyboardButton("📂 Kategori Favorit", callback_data="kategori")],
            [InlineKeyboardButton("ℹ️ Bantuan", callback_data="bantuan")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("👋 Selamat datang di Bot Shopee Affiliate!", reply_markup=reply_markup)

# =====================
# 🎮 Callback Handler
# =====================
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "promo":
        await query.edit_message_text("🛍️ Promo hari ini belum diinput admin.")
    elif data == "flashsale":
        await query.edit_message_text("⚡ Tidak ada flash sale aktif saat ini.")
    elif data == "kategori":
        await query.edit_message_text("📂 Silakan pilih kategori favoritmu (fitur coming soon).")
    elif data == "bantuan":
        await query.edit_message_text("ℹ️ Gunakan bot ini untuk dapatkan promo Shopee Affiliate setiap hari!")
    elif data == "tambah_produk":
        await query.edit_message_text("➕ Format tambah produk:\n\n/tambah Nama | Kategori | Harga1 | Harga2 | Link | Deskripsi | 0 | 1")
    elif data == "lihat_produk":
        cursor.execute("SELECT id, nama, harga_diskon FROM produk LIMIT 5")
        produk = cursor.fetchall()
        if not produk:
            await query.edit_message_text("📋 Belum ada produk tersimpan.")
        else:
            teks = "📋 Produk Tersimpan:\n\n"
            for p in produk:
                teks += f"ID {p[0]} - {p[1]} (Rp {p[2]})\n"
            await query.edit_message_text(teks)
    elif data == "broadcast":
        await query.edit_message_text("📢 Gunakan /broadcast {id} untuk kirim ke semua user.")
    elif data == "kirim_channel":
        await query.edit_message_text("📤 Gunakan /kirim_channel {id} untuk kirim ke channel.")

# =====================
# 📝 Tambah Produk
# =====================
async def tambah(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if str(update.effective_user.id) != str(ADMIN_ID):
        return await update.message.reply_text("❌ Kamu bukan admin.")
    
    try:
        text = " ".join(context.args)
        nama, kategori, harga_awal, harga_diskon, link, deskripsi, flashsale, aktif = text.split("|")
        cursor.execute("INSERT INTO produk (nama, kategori, harga_awal, harga_diskon, link, deskripsi, flashsale, aktif) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (nama.strip(), kategori.strip(), int(harga_awal), int(harga_diskon), link.strip(), deskripsi.strip(), int(flashsale), int(aktif))
        )
        conn.commit()
        await update.message.reply_text(f"✅ Produk '{nama}' berhasil ditambahkan!")
    except Exception as e:
        await update.message.reply_text(f"❌ Format salah. Gunakan:\n/tambah Nama | Kategori | Harga1 | Harga2 | Link | Deskripsi | 0 | 1\n\nError: {e}")

# =====================
# 📤 Kirim ke Channel
# =====================
async def kirim_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if str(update.effective_user.id) != str(ADMIN_ID):
        return await update.message.reply_text("❌ Kamu bukan admin.")
    
    if not context.args:
        return await update.message.reply_text("❌ Format salah. Gunakan: /kirim_channel {id_produk}")

    produk_id = context.args[0]
    cursor.execute("SELECT nama, kategori, harga_awal, harga_diskon, link, deskripsi FROM produk WHERE id = ?", (produk_id,))
    produk = cursor.fetchone()
    
    if not produk:
        return await update.message.reply_text("❌ Produk tidak ditemukan.")
    
    teks = f"🔥 {produk[0]} ({produk[1]})\n💸 Harga Awal: Rp {produk[2]}\n💰 Diskon: Rp {produk[3]}\n🔗 {produk[4]}\n📝 {produk[5]}"
    
    await context.bot.send_message(chat_id=CHANNEL_USERNAME, text=teks)
    await update.message.reply_text(f"✅ Produk berhasil dikirim ke {CHANNEL_USERNAME}!")

# =====================
# 🚀 Main
# =====================
def main():
    logging.basicConfig(level=logging.INFO)
    app = Application.builder().token(BOT_TOKEN).build()

    # Command
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("tambah", tambah))
    app.add_handler(CommandHandler("kirim_channel", kirim_channel))

    # Button Callback
    app.add_handler(CallbackQueryHandler(button_handler))

    app.run_polling()

if __name__ == "__main__":
    main()
