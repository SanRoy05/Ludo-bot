import logging
import uvicorn
from fastapi import FastAPI, Request, Response
from pyrogram.types import Update
from pyrogram import types

from config import BOT_TOKEN, WEBHOOK_URL
from bot import app as bot_app
import db

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("FastAPI")

fastapi_app = FastAPI()

@fastapi_app.on_event("startup")
async def on_startup():
    # Initialize DB Pool
    await db.init_db()
    
    # Start Pyrogram Client (without polling)
    await bot_app.start()
    
    # Set Webhook if URL is provided
    if WEBHOOK_URL:
        logger.info(f"Setting webhook to: {WEBHOOK_URL}")
        try:
            # Pyrogram doesn't have a built-in set_webhook method.
            # We can use the raw API via invoke or just a simple HTTP request.
            # For simplicity, we'll try to use invoke with raw Telegram functions.
            from pyrogram.raw import functions
            await bot_app.invoke(functions.account.UpdateStatus(offline=False)) # Just a ping
            # Actually, the easiest way is to use a simple HTTP GET to Telegram API since we have the token.
            import httpx
            async with httpx.AsyncClient() as client:
                url = f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook?url={WEBHOOK_URL}"
                resp = await client.get(url)
                if resp.status_code == 200:
                    logger.info("Webhook set successfully via API.")
                else:
                    logger.error(f"Failed to set webhook: {resp.text}")
        except Exception as e:
            logger.error(f"Error setting webhook: {e}")
    else:
        logger.warning("WEBHOOK_URL not set. Skipping webhook registration.")

@fastapi_app.on_event("shutdown")
async def on_shutdown():
    await bot_app.stop()

@fastapi_app.post("/webhook")
async def telegram_webhook(request: Request):
    try:
        update_json = await request.json()
        
        # 1. Basic Idempotency Check
        update_id = update_json.get("update_id")
        if update_id:
            if await db.is_update_processed(update_id):
                return Response(status_code=200)
            await db.mark_update_processed(update_id)

        # 2. Convert raw JSON to Pyrogram Update
        # Pyrogram's Client.process_update handles raw update objects.
        # We need to wrap it in a Update object or just pass it to process_update if supported.
        # Actually, pyrogram.types.Update is for internal use.
        # We can use bot_app.process_update(update_object)
        
        update = types.Update.read(update_json)
        # Note: Pyrogram expects an actual update object, not a dict.
        # However, bot.app.process_update takes the raw dict or object depending on version.
        # For most versions, passing the parsed Update object is correct.
        
        await bot_app.process_update(update)
        
        return Response(status_code=200)
    except Exception as e:
        logger.error(f"Error processing webhook: {e}")
        # Always return 200 to Telegram to stop retries
        return Response(status_code=200)

@fastapi_app.get("/")
async def root():
    return {"status": "ok", "bot": "LudoStateless"}

if __name__ == "__main__":
    uvicorn.run(fastapi_app, host="0.0.0.0", port=8000)
