from pyrogram import types
from db import db
from team_logic import get_team_id
from config import COLORS

async def join_handler(client, message, user=None):
    chat_id = message.chat.id
    user = user or message.from_user
    
    if user.is_bot:
        return
    
    game = await db.get_game(chat_id)
    if not game:
        is_team = message.text.startswith("/team") if message.text else False
        game_id = await db.create_game(chat_id, team_mode=is_team)
        game = await db.get_game(chat_id)
    
    if game['status'] != 'LOBBY':
        return await message.reply("Game already in progress.")
        
    if any(p['user_id'] == user.id for p in game['players']):
        return await message.reply("You are already in the lobby.")
        
    if len(game['players']) >= 4:
        return await message.reply("Lobby is full.")
        
    color = len(game['players'])
    team_id = get_team_id(color)
    
    await db.add_player(game['id'], user.id, user.username or user.first_name, color, team_id)
    
    game = await db.get_game(chat_id)
    players_text = "\n".join([f"{COLORS[p['color']]} @{p['username']}" for p in game['players']])
    
    mode_str = " (2v2 Team Mode)" if game['team_mode'] else ""
    text = f"**Ludo Lobby{mode_str}**\n\nPlayers:\n{players_text}\n\nNeed {4 - len(game['players'])} more players to start."
    keyboard = types.InlineKeyboardMarkup([[
        types.InlineKeyboardButton("Join Game", callback_data="join"),
        types.InlineKeyboardButton("Start Game", callback_data="start")
    ]])
    
    await message.reply(text, reply_markup=keyboard)

async def start_callback_handler(client, callback_query):
    chat_id = callback_query.message.chat.id
    game = await db.get_game(chat_id)
    
    if not game or game['status'] != 'LOBBY':
        return await callback_query.answer("No active lobby.")
        
    if len(game['players']) < 2:
        return await callback_query.answer("Need at least 2 players.", show_alert=True)
        
    await db.update_game_state(game['id'], status='PLAYING')
    await callback_query.message.edit_text("Game is starting! Rendering board...")
    
    # Import here to avoid circular
    from .game import send_board
    await send_board(client, chat_id)
