import os
from dotenv import load_dotenv

load_dotenv()

# Telegram API credentials
API_ID = int(os.getenv("API_ID", "32946705"))
API_HASH = os.getenv("API_HASH", "0575ff1e6e043aab8bbc9a4088f2e664")

# Session string for Railway persistence
SESSION_STRING = os.getenv("SESSION_STRING", "")

# Bot usernames
STACCERBOT_USERNAME = os.getenv("STACCERBOT_USERNAME", "staccerbot")
KIMFEETGURU_BOT_USERNAME = os.getenv("KIMFEETGURU_BOT_USERNAME", "kimfeetguru_bot")

# Server configuration
PORT = int(os.getenv("PORT", "8000"))

# Timeouts (in seconds)
BOT_RESPONSE_TIMEOUT = int(os.getenv("BOT_RESPONSE_TIMEOUT", "30"))
PHOTO_DOWNLOAD_TIMEOUT = int(os.getenv("PHOTO_DOWNLOAD_TIMEOUT", "60"))
