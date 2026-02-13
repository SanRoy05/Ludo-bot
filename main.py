import os
import asyncio
from fastapi import FastAPI, Request
from pyrogram import types
from bot import app as bot_app
from db import db
from config import WEBHOOK_URL

import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

fastapi_app = FastAPI()

@fastapi_app.on_event("startup")
async def startup_event():
    try:
        # Initialize DB
        await db.init_db()
        logger.info("Database initialized.")
        # Start bot
        await bot_app.start()
        logger.info("Bot started.")
        if WEBHOOK_URL:
            await bot_app.set_webhook(f"{WEBHOOK_URL}/webhook")
            logger.info(f"Webhook set to {WEBHOOK_URL}/webhook")
    except Exception as e:
        logger.error(f"Startup failed: {e}", exc_info=True)
        raise e

@fastapi_app.on_event("shutdown")
async def shutdown_event():
    await bot_app.stop()
    await db.disconnect()

@fastapi_app.post("/webhook")
async def telegram_webhook(request: Request):
    update = await request.json()
    # Convert dict to Pyrogram update
    # In practice, Pyrogram's webhook server is often separate, 
    # but for FastAPI we can feed it manually or use bot_app.dispatch
    telegram_update = types.Update.parse(update)
    # Pyrogram usually expects raw updates via a specific internal method
    # For a stateless Render deploy, we can just process it:
    await bot_app.process_update(telegram_update)
    return {"status": "ok"}

@fastapi_app.get("/")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    # Render provides PORT environment variable
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(fastapi_app, host="0.0.0.0", port=port)
