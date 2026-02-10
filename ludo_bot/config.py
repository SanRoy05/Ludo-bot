import os
from dotenv import load_dotenv

load_dotenv()

API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")

if not all([API_ID, API_HASH, BOT_TOKEN]):
    raise ValueError("API_ID, API_HASH, and BOT_TOKEN must be set in the .env file.")

DATABASE_PATH = os.getenv("DATABASE_PATH", "ludo_game.db")
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
