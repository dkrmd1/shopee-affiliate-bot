# config.py
import os

def get_config():
    """
    Ambil konfigurasi dari environment variables, 
    kalau tidak ada gunakan fallback default.
    """
    return {
        'BOT_TOKEN': os.getenv('BOT_TOKEN', '8324792358:AAGXjXwm1U5cBs5c5Gd8VA3KVtYfxPVSPWA'),
        'ADMIN_ID': int(os.getenv('ADMIN_ID', '123456789')),  # Ganti fallback sesuai User ID kamu
        'CHANNEL_ID': os.getenv('CHANNEL_ID', '@promoshopee22a'),
        'CHANNEL_USERNAME': os.getenv('CHANNEL_USERNAME', '@promoshopee22a'),
        'PORT': int(os.getenv('PORT', '8080'))
    }

def print_config():
    """
    Cetak konfigurasi untuk debugging, BOT_TOKEN hanya ditampilkan sebagian.
    """
    config = get_config()
    print("🔧 Configuration loaded:")
    for key, value in config.items():
        if key == 'BOT_TOKEN':
            print(f"✅ {key}: {value[:15]}... (hidden)")
        else:
            print(f"✅ {key}: {value}")
    return config
