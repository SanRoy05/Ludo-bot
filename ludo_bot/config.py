import os
from dotenv import load_dotenv

load_dotenv()

API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")

if not all([API_ID, API_HASH, BOT_TOKEN]):
    raise ValueError(
        "Missing required environment variables (API_ID, API_HASH, BOT_TOKEN).\n"
        "Please add them in your Render Service Dashboard -> Environment section."
    )

DATABASE_URL = os.getenv("DATABASE_URL")
WEBHOOK_URL = os.getenv("WEBHOOK_URL") # e.g. https://your-app.onrender.com/webhook
TURN_TIMEOUT = int(os.getenv("TURN_TIMEOUT", 90))

# Colors and Emojis
COLORS = {
    0: "🔴",  # RED
    1: "🟡",  # YELLOW
    2: "🟢",  # GREEN
    3: "🔵",  # BLUE
}

# Ludo Board Constants
BOARD_SIZE = 15
SAFE_POSITIONS = [1, 9, 14, 22, 27, 35, 40, 48]
HOME_THRESHOLD = 51  # Position before entering home path
HOME_PATH_LENGTH = 6
TOTAL_PATH_LENGTH = 57 # 51 + 6
