import asyncio
import sys
import time
import logging
from typing import Dict

# 1. SETUP EVENT LOOP
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# 2. CONFIGURE LOGGING
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("LudoBot")

# 3. NOW IMPORT PYROGRAM AND OTHER MODULES
from pyrogram import Client, filters, enums
from pyrogram.types import (
    InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, Message,
    BotCommand, BotCommandScopeAllPrivateChats, BotCommandScopeAllGroupChats
)
from pyrogram.handlers import MessageHandler, CallbackQueryHandler
from pyrogram.errors import FloodWait, Forbidden, ChatAdminRequired

from config import API_ID, API_HASH, BOT_TOKEN, COLORS, TURN_TIMEOUT
from ludo.manager import LudoManager, TournamentManager
from ludo.state import Match
from ludo.render import render_board
import db

# 4. BOT STATE (Managers are now stateless)
manager = LudoManager()
t_manager = TournamentManager()

# 5. GAME FUNCTIONS
async def refresh_game_view(client: Client, message: Message, state):
    board_text = render_board(state)
    current_p = state.players[state.current_turn_index]
    
    # Update timeout check here since background loop is removed
    # This is a passive check: if someone interacts and it's past timeout, we skip
    now = time.time()
    if not state.is_lobby and state.last_roll_time > 0:
        if now - state.last_roll_time > TURN_TIMEOUT:
             state.current_turn_index = (state.current_turn_index + 1) % len(state.players)
             state.dice_value = None
             state.last_roll_time = now
             await db.save_game_state(state.chat_id, state.to_dict())
             current_p = state.players[state.current_turn_index]

    status_text = f"Turn: {COLORS[current_p.color_index]} **{current_p.first_name}**"
    if state.dice_value:
        status_text += f" (Rolled: {state.dice_value})"
    
    text = f"🕹 **Ludo Game**\n{status_text}\n\n<code>{board_text}</code>"
    if state.match_id:
        text = f"🏆 **Tournament Match: {state.match_id}**\n" + text
    
    match_suffix = f":{state.match_id}" if state.match_id else ""
    buttons = []
    if state.dice_value is None:
        buttons.append([InlineKeyboardButton(f"🎲 Roll Dice ({current_p.first_name})", callback_data=f"ludo:roll:{match_suffix}")])
    else:
        from ludo.rules import get_valid_moves
        valid_moves = get_valid_moves(current_p, state.dice_value)
        row = []
        for v in valid_moves:
            token = current_p.tokens[v]
            label = f"{COLORS[current_p.color_index]} Token {v+1}"
            if token.state == "home": label += " (Home)"
            row.append(InlineKeyboardButton(label, callback_data=f"ludo:move:{v}:{match_suffix}"))
        
        if row: 
            for i in range(0, len(row), 2):
                buttons.append(row[i:i+2])
        else:
            buttons.append([InlineKeyboardButton("❌ No Moves - Skip", callback_data=f"ludo:roll:{match_suffix}")])
    
    try:
        await message.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons), parse_mode=enums.ParseMode.HTML)
    except Exception as e:
        logger.warning(f"Failed to edit game message: {e}")

# 6. BROADCAST & TRACKING
async def track_chats(client, message):
    if not message.chat: return
    chat_id = message.chat.id
    chat_type = "private" if message.chat.type == enums.ChatType.PRIVATE else "group"
    await db.add_active_chat(chat_id, chat_type)

async def cmd_broadcast(client, message):
    # For safety on Render, we omit the interactive "waiting for broadast" state
    # and just allow /broadcast [msg]
    if len(message.command) < 2:
        return await message.reply("Usage: /broadcast [message]")
    
    member = await client.get_chat_member(message.chat.id, message.from_user.id)
    if member.status not in [enums.ChatMemberStatus.ADMINISTRATOR, enums.ChatMemberStatus.OWNER]:
        return await message.reply("Only admins can use the broadcast command!")
    
    last_b = await db.get_last_broadcast()
    if time.time() - last_b < 86400:
        remaining = 24 - (time.time() - last_b) / 3600
        return await message.reply(f"⚠️ **Broadcast limit reached.**\nYou can broadcast again in {remaining:.1f} hours.")

    content = message.text.split(None, 1)[1]
    await message.reply(f"🚀 **Starting Broadcast...**")
    
    chats = await db.get_active_chats()
    success, failed = 0, 0
    formatted_msg = f"📢 **Update**\n\n{content}"
    
    for chat_id, chat_type in chats:
        try:
            await client.send_message(chat_id, formatted_msg)
            success += 1
            await asyncio.sleep(0.5) 
        except FloodWait as e:
            await asyncio.sleep(e.value)
            try:
                await client.send_message(chat_id, formatted_msg)
                success += 1
            except: failed += 1
        except (Forbidden, ChatAdminRequired):
            await db.remove_active_chat(chat_id)
            failed += 1
        except Exception:
            failed += 1
            
    await db.set_last_broadcast(time.time())
    await message.reply(f"✅ **Broadcast Complete!**\n\n📈 **Stats:**\n- Success: {success}\n- Failed: {failed}")

async def set_scoped_commands(app: Client):
    private_commands = [
        BotCommand("start", "Start bot & show info"),
        BotCommand("help", "Show help"),
        BotCommand("credits", "Show user credits"),
        BotCommand("ludorank", "Show global rankings"),
        BotCommand("season", "Show current season info"),
    ]
    await app.set_bot_commands(private_commands, scope=BotCommandScopeAllPrivateChats())

    group_commands = [
        BotCommand("startludo", "Start a Ludo game"),
        BotCommand("ludostop", "Stop current Ludo game (admin only)"),
        BotCommand("ludostate", "Show current game state"),
        BotCommand("ludotournament", "Create a Ludo tournament"),
        BotCommand("join", "Join game or tournament"),
    ]
    await app.set_bot_commands(group_commands, scope=BotCommandScopeAllGroupChats())

async def launch_match(client, chat_id, match: Match, tournament_id: str):
    await manager.create_lobby(chat_id, 0, "", match_id=match.match_id, players=match.players)
    state = await manager.get_game_state(chat_id, match_id=match.match_id)
    if state:
        state.tournament_id = tournament_id
        await manager.start_game(chat_id, 0, match_id=match.match_id)
        
        p_names = []
        for uid in match.players:
            try:
                u = await client.get_users(uid)
                p_names.append(u.first_name)
            except: p_names.append(f"Player {uid}")
        
        text = f"⚔️ **Match Start: {match.match_id}**\n{p_names[0]} vs {p_names[1]}"
        msg = await client.send_message(chat_id, text)
        await refresh_game_view(client, msg, state)

# 7. COMMAND HANDLERS
async def cmd_start(client, message):
    if message.chat.type != enums.ChatType.PRIVATE:
        return await message.reply("🎲 **Ludo Bot is active!** Use /startludo to begin.")

    me = await client.get_me()
    first_name = message.from_user.first_name
    caption = (
        f"Hey {first_name} 👋\n\n"
        "🎲 **This is LudoXBot!**\n"
        "A fast & fun multiplayer Ludo game for Telegram groups.\n\n"
        "➕ Add me to a group to start playing."
    )
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("✨ ADD ME TO YOUR GROUP ✨", url=f"https://t.me/{me.username}?startgroup=true")],
        [InlineKeyboardButton("SUPPORT", url="https://t.me/cosysx_community"), InlineKeyboardButton("❤️ OWNER ❤️", url="https://t.me/noneQ_0")],
        [InlineKeyboardButton("UPDATES ♪", url="https://t.me/cosysx"), InlineKeyboardButton("🌐 LANGUAGE", callback_data="lang:menu")],
        [InlineKeyboardButton("♡ HELP AND COMMAND ♡", callback_data="help:menu")]
    ])
    await message.reply_text(caption, reply_markup=keyboard)

async def cmd_help(client, message):
    text = (
        "📖 **Ludo Bot Help**\n\n"
        "**Groups:**\n"
        "/startludo - Create a new game lobby\n"
        "/join - Join a lobby or tournament\n"
        "/ludostate - Show current game board\n"
        "/ludostop - End current game (Admins)\n"
        "/ludotournament - Start a tournament"
    )
    await message.reply(text)

async def cmd_ludostop(client, message):
    if message.chat.type in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
        member = await client.get_chat_member(message.chat.id, message.from_user.id)
        if member.status not in [enums.ChatMemberStatus.ADMINISTRATOR, enums.ChatMemberStatus.OWNER]:
            return await message.reply("Only admins can stop the game!")
    
    if await manager.delete_game(message.chat.id):
        await message.reply("🛑 **Game stopped and lobby cleared.**")
    else:
        await message.reply("No active game to stop.")

async def cmd_ludostate(client, message):
    state = await manager.get_game_state(message.chat.id)
    if not state:
        return await message.reply("No active game. Use /startludo to begin!")
    
    if state.is_lobby:
        p_list = "\n".join([f"{i+1}. {p.first_name}" for i, p in enumerate(state.players)])
        await message.reply(f"🎮 **Ludo Lobby - Waiting for players**\n\n{p_list}")
    else:
        board_text = render_board(state)
        current_p = state.players[state.current_turn_index]
        text = f"🕹 **Current Game State**\nTurn: {COLORS[current_p.color_index]} **{current_p.first_name}**\n\n<code>{board_text}</code>"
        await message.reply(text, parse_mode=enums.ParseMode.HTML)

async def cmd_join(client, message):
    chat_id, user_id, user_name = message.chat.id, message.from_user.id, message.from_user.first_name
    msg = await manager.join_lobby(chat_id, user_id, user_name)
    await message.reply(msg)

async def cmd_startludo(client, message):
    if message.chat.type not in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
        return await message.reply("This bot only works in groups!")
    err = await manager.create_lobby(message.chat.id, message.from_user.id, message.from_user.first_name)
    if err: return await message.reply(err)
    text = f"🎮 **Ludo Lobby**\n\n1. {message.from_user.first_name}\n\n_Minimum 2 players to start._"
    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("➕ Join", callback_data="ludo:join"), InlineKeyboardButton("▶️ Start Game", callback_data="ludo:start")]])
    await message.reply(text, reply_markup=keyboard)

async def cmd_ludorank(client, message):
    leaderboard = await db.get_leaderboard()
    if not leaderboard: return await message.reply("No rankings yet.")
    text = "🏆 **Global Ludo Rankings**\n\n"
    for i, (name, rating, wins) in enumerate(leaderboard, 1):
        medal = "🥇" if i == 1 else ("🥈" if i == 2 else ("🥉" if i == 3 else f"{i}."))
        text += f"{medal} **{name}**\n   Rating: `{rating}` | Wins: `{wins}`\n"
    await message.reply(text)

async def cmd_credits(client, message):
    balance = await db.get_credits(message.from_user.id)
    await message.reply(f"💰 **Your Balance:** `{balance} credits`")

async def cmd_tournament_lobby(client, message):
    t_id = await t_manager.create_tournament(message.from_user.id)
    text = f"🏆 **Ludo Tournament Created!**\nTournament ID: `{t_id}`\n\nPlayers: 1/16\n1. {message.from_user.first_name}"
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Join", callback_data=f"tourney:join:{t_id}")],
        [InlineKeyboardButton("▶️ Start Tournament", callback_data=f"tourney:start:{t_id}")]
    ])
    await message.reply(text, reply_markup=keyboard)

# 8. CALLBACK HANDLER
async def handle_callback(client, query):
    data = query.data.split(":")
    if data[0] != "ludo": return
    
    action = data[1]
    match_id = data[3] if len(data) > 3 else (data[2] if len(data) > 2 and action in ["roll", "join", "start"] else None)
    chat_id, user_id, user_name = query.message.chat.id, query.from_user.id, query.from_user.first_name
    
    state = await manager.get_game_state(chat_id, match_id=match_id)
    if not state: return await query.answer("Game not found.", show_alert=True)

    if action == "join":
        msg = await manager.join_lobby(chat_id, user_id, user_name)
        await query.answer(msg)
        if "joined" in msg:
            p_list = "\n".join([f"{i+1}. {p.first_name}" for i, p in enumerate(state.players)])
            await query.edit_message_text(f"🎮 **Ludo Lobby**\n\n{p_list}", reply_markup=query.message.reply_markup)
    elif action == "start":
        if user_id != state.players[0].user_id:
            return await query.answer("Only the creator can start.", show_alert=True)
        msg = await manager.start_game(chat_id, user_id)
        if "started" in msg:
            await query.answer("Starting...")
            await refresh_game_view(client, query.message, state)
        else: await query.answer(msg, show_alert=True)
    elif action == "roll":
        val, msg = await manager.roll_dice(chat_id, user_id, match_id=match_id)
        if val is not None:
            await query.answer(f"You rolled {val}!")
            await refresh_game_view(client, query.message, state)
        else:
            await query.answer(msg, show_alert=True)
            if "Skipping" in msg: await refresh_game_view(client, query.message, state)
    elif action == "move":
        token_id = int(data[2])
        msg = await manager.move_token(chat_id, user_id, token_id, match_id=match_id)
        await query.answer(msg)
        if "won" in msg:
            await query.edit_message_text(f"🏁 **GAME OVER**\n\n{msg}")
            if state.match_id and state.tournament_id:
                await t_manager.set_match_winner(state.tournament_id, state.match_id, user_id)
                # Note: Automated round launching omitted for stateless safety,
                # would require a more complex trigger or task queue.
        else:
            await refresh_game_view(client, query.message, state)

async def handle_tourney_callback(client, query):
    data = query.data.split(":")
    action, t_id = data[1], data[2]
    user_id, user_name = query.from_user.id, query.from_user.first_name
    t = await t_manager.get_tournament(t_id)
    if not t: return await query.answer("Tournament not found.")

    if action == "join":
        msg = await t_manager.join_tournament(t_id, user_id)
        await query.answer(msg)
        if "successfully" in msg:
            await query.edit_message_text(f"🏆 **Ludo Tournament**\nID: `{t_id}`\n\nPlayers: {len(t.players)+1}/16", reply_markup=query.message.reply_markup)
    elif action == "start":
        if user_id != t.players[0]: return await query.answer("Only the creator can start.")
        err = await t_manager.start_tournament(t_id)
        if err: return await query.answer(err, show_alert=True)
        await query.answer("Started! Launching matches...")
        for match in t.rounds[0]:
            await launch_match(client, query.message.chat.id, match, t_id)

async def handle_dashboard_callback(client, query):
    if query.data == "help:menu":
        text = "📖 **Ludo Bot Help**\n\nAdd bot to group, send /startludo, join and play!"
        await query.edit_message_caption(caption=text, reply_markup=query.message.reply_markup)
    elif query.data == "lang:menu":
        await query.answer("Only English supported currently.", show_alert=True)

# 9. INITIALIZATION
def setup_handlers(app: Client):
    app.add_handler(MessageHandler(cmd_broadcast, filters.command("broadcast")))
    app.add_handler(MessageHandler(cmd_start, filters.command("start")))
    app.add_handler(MessageHandler(cmd_help, filters.command("help")))
    app.add_handler(MessageHandler(cmd_startludo, filters.command("startludo")))
    app.add_handler(MessageHandler(cmd_ludostop, filters.command(["ludostop", "stop"])))
    app.add_handler(MessageHandler(cmd_ludostate, filters.command("ludostate")))
    app.add_handler(MessageHandler(cmd_join, filters.command("join")))
    app.add_handler(MessageHandler(cmd_ludorank, filters.command("ludorank")))
    app.add_handler(MessageHandler(cmd_credits, filters.command("credits")))
    app.add_handler(MessageHandler(cmd_tournament_lobby, filters.command(["ludotournament", "jointournament"])))
    app.add_handler(MessageHandler(track_chats, filters.all), group=-1)
    app.add_handler(CallbackQueryHandler(handle_callback, filters.regex("^ludo:")))
    app.add_handler(CallbackQueryHandler(handle_tourney_callback, filters.regex("^tourney:")))
    app.add_handler(CallbackQueryHandler(handle_dashboard_callback, filters.regex("^(help|lang):")))

app = Client("ludo_bot_session", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN, plugins=None)
setup_handlers(app)
