import os

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")

# Absolute pathes to block files
ESCALATED_IP_FILE = "/home/arkain123/apps/mare.by/escalated_ip.txt"
BLOCKED_IP_FILE = "/home/arkain123/apps/mare.by/blocked_ip.txt"

BANNED_EXTENSIONS = {
    'exe', 'scr', 'cpl', 'docm',
    'jar', 'html', 'htm', 'sh', 'bat', 'cmd',
    'js', 'vbs', 'ps1', 'msi', 'dll', 'so'
}

MAX_FILE_SIZE = 100 * 1024 * 1024  # 100 MB

# Telegram
TG_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TG_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
TG_ADMIN_IDS = {
    x.strip() for x in os.getenv("TELEGRAM_ADMIN_IDS", "").split(",") if x.strip()
}
TG_WEBHOOK_SECRET = os.getenv("TELEGRAM_WEBHOOK_SECRET", "")

# Base domain and mirrors
BASE_URL = "https://mare.by"
MIRRORS = ["https://mare.by", "https://mare.of.by"]
