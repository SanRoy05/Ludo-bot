import os
from dotenv import load_dotenv

load_dotenv()

API_ID = int(os.getenv("API_ID")) if os.getenv("API_ID") else None
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")

DATABASE_URL = os.getenv("DATABASE_URL")

if not all([API_ID, API_HASH, BOT_TOKEN, DATABASE_URL]):
    missing = [v for v in ["API_ID", "API_HASH", "BOT_TOKEN", "DATABASE_URL"] if not os.getenv(v)]
    raise ValueError(
        f"Missing required environment variables: {', '.join(missing)}.\n"
        "Please add them in your Render Service Dashboard -> Environment section.\n"
        "If you haven't created a database yet, create a 'Render PostgreSQL' and copy the 'Internal Database URL'."
    )

WEBHOOK_URL = os.getenv("WEBHOOK_URL") # e.g. https://your-app.onrender.com/webhook
TURN_TIMEOUT = int(os.getenv("TURN_TIMEOUT", 90))

# Colors and Emojis
COLORS = {
    0: "🔴",  # RED (Top-Left)
    1: "🟢",  # GREEN (Top-Right)
    2: "🟡",  # YELLOW (Bottom-Right)
    3: "🔵",  # BLUE (Bottom-Left)
}

# Ludo Board Constants
BOARD_SIZE = 15
SAFE_POSITIONS = [10, 15, 23, 28, 36, 41, 49, 2]
HOME_THRESHOLD = 51  # Not used anymore by the new threshold logic but kept for safety
HOME_PATH_LENGTH = 6
TOTAL_PATH_LENGTH = 57 # 51 + 6
