# Ludo Bot - Telegram Bot Game

A Telegram bot implementation for playing Ludo game.

## Setup Instructions

### Local Development

1. Clone the repository:
```bash
git clone https://github.com/SanRoy05/ludo-bot-.git
cd ludo-bot
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Configure environment variables:
```bash
cp .env.example .env
# Edit .env with your Telegram API credentials
```

5. Run the bot:
```bash
cd ludo_bot
python bot.py
```

### Deploy to Fly.io

1. Install Fly CLI: https://fly.io/docs/getting-started/installing-flyctl/

2. Authenticate:
```bash
flyctl auth login
```

3. Create a Fly app (first time only):
```bash
flyctl apps create ludo-bot
```

4. Set environment variables:
```bash
flyctl secrets set API_ID=your_api_id API_HASH=your_api_hash BOT_TOKEN=your_bot_token
```

5. Deploy:
```bash
flyctl deploy
```

6. View logs:
```bash
flyctl logs
```

## Project Structure

```
ludo-bot/
├── ludo_bot/
│   ├── bot.py           # Main bot file
│   ├── config.py        # Configuration
│   ├── db.py            # Database operations
│   └── ludo/            # Game logic
│       ├── rules.py
│       ├── state.py
│       ├── manager.py
│       └── render.py
├── requirements.txt     # Python dependencies
├── fly.toml             # Fly.io configuration
├── Dockerfile           # Docker configuration
└── README.md
```

## Dependencies

- pyrogram - Telegram Bot API client
- tgcrypto - Encryption support
- aiosqlite - Async SQLite database
- python-dotenv - Environment variable management

## License

MIT
