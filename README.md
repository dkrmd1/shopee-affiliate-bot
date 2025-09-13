# 🛍️ Bot Shopee Affiliate dengan Channel

Bot Telegram untuk mengirim promo Shopee dengan sistem affiliate dan channel publik berbahasa Indonesia.

## 📋 Fitur Utama

### 🤖 **Bot Features:**
- ✅ **Wajib Subscribe Channel** - User harus subscribe channel dulu
- ✅ **Promo Harian** - Broadcast otomatis jam 8 pagi & 8 malam  
- ✅ **Flash Sale Alert** - Notifikasi flash sale real-time
- ✅ **Kategori Produk** - User bisa pilih kategori favorit
- ✅ **Admin Dashboard** - Manage produk via command
- ✅ **Database SQLite** - Semua data tersimpan otomatis

### 📢 **Channel Features:**
- ✅ **Auto Post** - Produk otomatis dikirim ke channel
- ✅ **Format Menarik** - Template pesan yang eye-catching
- ✅ **Link Affiliate** - Setiap produk ada link affiliate Shopee

## 🎮 Command Reference

### **👑 Command Admin:**

#### Tambah Produk:
```bash
/tambah iPhone 15 Pro | Elektronik | 15999000 | 12999000 | https://shopee.co.id/xxx?af_siteid=123 | Garansi resmi iBox 1 tahun | 0 | 1
```

#### Management Produk:
- `/lihat_produk` - Lihat semua produk
- `/kirim_channel {id}` - Kirim produk ke channel
- `/broadcast {id}` - Broadcast ke semua user

### **👥 Command User:**
- `/start` - Mulai bot & cek subscribe
- `/promo` - Promo hari ini
- `/flashsale` - Flash sale aktif
- `/kategori` - Pilih kategori favorit

## 🚀 Setup Railway

1. Push code ke GitHub
2. Connect GitHub repo ke Railway
3. Set Environment Variables:
   - `BOT_TOKEN` = token dari BotFather
   - `ADMIN_ID` = Telegram ID Anda
   - `CHANNEL_ID` = @nama_channel
   - `CHANNEL_USERNAME` = @nama_channel
4. Deploy otomatis

## 💰 Monetisasi

### **Estimasi Earning:**
- 1000 subscriber aktif
- 50 transaksi/hari @ Rp 200k
- Komisi 5% = Rp 500k/hari
- **Monthly: ~Rp 15 juta**

## 🔄 Workflow Harian

### **Admin (10 menit/hari):**
```bash
# Input produk
/tambah Produk A | Kategori | Harga1 | Harga2 | Link | Desc | 0 | 1

# Kirim ke channel
/kirim_channel 1

# Broadcast ke user  
/broadcast 1
```

### **Otomatis:**
- ✅ Bot format pesan menarik
- ✅ Post ke channel publik
- ✅ Notifikasi ke user bot
- ✅ Schedule broadcast jam 8 pagi & malam
- ✅ User management & subscribe checking

---
**🚀 Created for Railway Deployment**  
**📱 Shopee Affiliate Bot + Channel System**  
**🇮🇩 Bahasa Indonesia**