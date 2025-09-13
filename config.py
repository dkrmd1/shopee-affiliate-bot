# config.py
import os

# Fungsi untuk mengambil environment variables dengan fallback
def get_config():
    config = {
        'BOT_TOKEN': os.getenv('BOT_TOKEN') or '8324792358:AAGXjXwm1U5cBs5c5Gd8VA3KVtYfxPVSPWA',
        'ADMIN_ID': int(os.getenv('ADMIN_ID', '123456789')),  # Ganti dengan User ID Anda
        'CHANNEL_ID': os.getenv('CHANNEL_ID') or '@promoshopee22a',
        'CHANNEL_USERNAME': os.getenv('CHANNEL_USERNAME') or '@promoshopee22a',
        'PORT': int(os.getenv('PORT', '8080'))
    }
    
    return config

# Untuk debugging
def print_config():
    config = get_config()
    print("🔧 Configuration loaded:")
    for key, value in config.items():
        if key == 'BOT_TOKEN':
            print(f"✅ {key}: {str(value)[:20]}...")
        else:
            print(f"✅ {key}: {value}")
    return config