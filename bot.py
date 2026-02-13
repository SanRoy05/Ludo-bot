from pyrogram import Client, filters
from config import API_ID, API_HASH, BOT_TOKEN
from handlers.lobby import join_handler, start_callback_handler
from handlers.game import roll_handler, move_handler
from handlers.stats import help_handler, stats_handler, credits_handler

app = Client(
    "ludo_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
    plugins=None
)

@app.on_message(filters.command("start"))
async def start_cmd(client, message):
    if message.chat.type == "private":
        from handlers.menu import send_dashboard
        await send_dashboard(client, message)
    else:
        # Standard group welcome/help
        await help_handler(client, message)

@app.on_message(filters.command("help"))
async def help_cmd(client, message):
    await help_handler(client, message)

@app.on_message(filters.command("staterank"))
async def stats_cmd(client, message):
    await stats_handler(client, message)

@app.on_message(filters.command("seasoncredits"))
async def credits_cmd(client, message):
    await credits_handler(client, message)

@app.on_message(filters.command("ludo") & filters.group)
async def ludo_cmd(client, message):
    await join_handler(client, message)

@app.on_callback_query()
async def callback_query_handler(client, callback_query):
    data = callback_query.data
    
    if data == "join":
        # Handle join logic directly or via lobby.py
        from handlers.lobby import join_handler
        # Pass the callback user explicitly
        await join_handler(client, callback_query.message, user=callback_query.from_user)
        await callback_query.answer()
        
    elif data == "start":
        await start_callback_handler(client, callback_query)
        
    elif data == "roll":
        await roll_handler(client, callback_query)
        
    elif data.startswith("move_"):
        token_idx = int(data.split("_")[1])
        await move_handler(client, callback_query, token_idx)
        
    elif data == "skip":
        from handlers.game import skip_turn, send_board
        from db import db
        game = await db.get_game(callback_query.message.chat.id)
        await skip_turn(game)
        await send_board(client, callback_query.message.chat.id, callback_query.message.id)
        await callback_query.answer("Turn skipped.")
        
    elif data == "help:menu":
        from handlers.menu import help_menu_handler
        await help_menu_handler(client, callback_query)
        
    elif data == "lang:menu":
        from handlers.menu import lang_menu_handler
        await lang_menu_handler(client, callback_query)
        
    elif data == "menu:back":
        from handlers.menu import back_to_menu_handler
        await back_to_menu_handler(client, callback_query)
