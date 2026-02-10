import asyncio
import sys
import time
import logging
from typing import Dict

# 1. SETUP EVENT LOOP BEFORE ANY PYROGRAM IMPORTS
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

try:
    loop = asyncio.get_event_loop()
except RuntimeError:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

# 2. CONFIGURE LOGGING
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("LudoBot")

# 3. NOW IMPORT PYROGRAM AND OTHER MODULES
from pyrogram import Client, filters, enums, idle
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

# 4. BOT STATE
manager = LudoManager()
t_manager = TournamentManager()
game_messages: Dict[int, Message] = {} 
broadcast_admin: Dict[int, bool] = {} # user_id: True if waiting for broadcast content

# 5. GAME FUNCTIONS
async def timeout_checker():
    logger.info("Timeout checker started.")
    while True:
        try:
            now = time.time()
            for key, state in list(manager.games.items()):
                if not state.is_lobby and state.last_roll_time > 0:
                    if now - state.last_roll_time > TURN_TIMEOUT:
                        chat_id = state.chat_id
                        logger.info(f"Timeout in {chat_id}")
                        current_p = state.players[state.current_turn_index]
                        state.current_turn_index = (state.current_turn_index + 1) % len(state.players)
                        state.dice_value = None
                        state.last_roll_time = now
                        if chat_id in game_messages:
                            try:
                                await refresh_game_view(game_messages[chat_id], state)
                            except: pass
        except Exception as e:
            logger.error(f"Timeout checker error: {e}")
        await asyncio.sleep(5)

async def refresh_game_view(message: Message, state):
    board_text = render_board(state)
    current_p = state.players[state.current_turn_index]
    state.last_roll_time = time.time()
    game_messages[state.chat_id] = message
    
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
    
    await message.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons), parse_mode=enums.ParseMode.HTML)

# 6. BROADCAST & TRACKING
async def track_chats(client, message):
    """Automatically track active chats that interact with the bot."""
    if not message.chat: return
    chat_id = message.chat.id
    chat_type = "private" if message.chat.type == enums.ChatType.PRIVATE else "group"
    await db.add_active_chat(chat_id, chat_type)

async def cmd_broadcast(client, message):
    # Only admins can broadcast (check owner or admin status)
    # For now, we'll allow owners and admins of the group where the command is sent, 
    # but usually, it's restricted to a specific BOT_OWNER_ID.
    # Let's check if the user is an admin in the chat OR use a hardcoded owner check.
    member = await client.get_chat_member(message.chat.id, message.from_user.id)
    if member.status not in [enums.ChatMemberStatus.ADMINISTRATOR, enums.ChatMemberStatus.OWNER]:
        return await message.reply("Only admins can use the broadcast command!")
    
    # Check 24h limit
    last_b = await db.get_last_broadcast()
    if time.time() - last_b < 86400: # 24 hours
        remaining = 24 - (time.time() - last_b) / 3600
        return await message.reply(f"⚠️ **Broadcast limit reached.**\nYou can broadcast again in {remaining:.1f} hours.")

    broadcast_admin[message.from_user.id] = True
    await message.reply("📢 **Broadcast System initiated.**\nPlease send the content for the announcement (Text, Stickers, etc.).")

async def handle_broadcast_message(client, message):
    user_id = message.from_user.id
    if user_id not in broadcast_admin: return
    
    del broadcast_admin[user_id]
    content = message.text if message.text else "Update" # Fallback
    
    # Start broadcast loop
    await message.reply(f"🚀 **Starting Broadcast...**\nPreparing to send to all active chats.")
    
    chats = await db.get_active_chats()
    success, failed = 0, 0
    
    formatted_msg = f"📢 **Update**\n\n{content}"
    
    for chat_id, chat_type in chats:
        try:
            await client.send_message(chat_id, formatted_msg)
            success += 1
            await asyncio.sleep(0.5) # Sequental send 0.5s interval
        except FloodWait as e:
            logger.warning(f"FloodWait: sleeping for {e.value} seconds")
            await asyncio.sleep(e.value)
            # Retry once
            try:
                await client.send_message(chat_id, formatted_msg)
                success += 1
            except: failed += 1
        except (Forbidden, ChatAdminRequired):
            # Bot blocked or removed, clean up DB
            logger.info(f"Removing inactive/blocked chat: {chat_id}")
            await db.remove_active_chat(chat_id)
            failed += 1
        except Exception as e:
            logger.error(f"Broadcast error for {chat_id}: {e}")
            failed += 1
            
    await db.set_last_broadcast(time.time())
    await message.reply(f"✅ **Broadcast Complete!**\n\n📈 **Stats:**\n- Success: {success}\n- Failed/Removed: {failed}")

async def set_scoped_commands(app: Client):
    """Register bot commands with specific scopes."""
    # 1. Private Chat Commands
    private_commands = [
        BotCommand("start", "Start bot & show info"),
        BotCommand("help", "Show help"),
        BotCommand("credits", "Show user credits"),
        BotCommand("ludorank", "Show global rankings"),
        BotCommand("season", "Show current season info"),
    ]
    await app.set_bot_commands(private_commands, scope=BotCommandScopeAllPrivateChats())

    # 2. Group Chat Commands
    group_commands = [
        BotCommand("startludo", "Start a Ludo game"),
        BotCommand("ludostop", "Stop current Ludo game (admin only)"),
        BotCommand("ludostate", "Show current game state"),
        BotCommand("ludotournament", "Create a Ludo tournament"),
        BotCommand("join", "Join game or tournament"),
    ]
    await app.set_bot_commands(group_commands, scope=BotCommandScopeAllGroupChats())
    
    logger.info("Scoped commands registered successfully.")

async def launch_match(client, chat_id, match: Match, tournament_id: str):
    # Register the match in Ludo manager
    manager.create_lobby(chat_id, 0, "", match_id=match.match_id, players=match.players)
    state = await manager.get_game_state(chat_id, match_id=match.match_id)
    state.tournament_id = tournament_id
    manager.start_game(chat_id, 0, match_id=match.match_id)
    
    # Send match start message
    p_names = []
    for uid in match.players:
        try:
            u = await client.get_users(uid)
            p_names.append(u.first_name)
        except: p_names.append(f"Player {uid}")
    
    text = f"⚔️ **Match Start: {match.match_id}**\n{p_names[0]} vs {p_names[1]}"
    msg = await client.send_message(chat_id, text)
    await refresh_game_view(msg, state)

# 6. COMMAND HANDLERS
async def cmd_start(client, message):
    if message.chat.type != enums.ChatType.PRIVATE:
        # Simple response for groups if they used /start (though set_bot_commands hide it there)
        return await message.reply("🎲 **Ludo Bot is active!** Use /startludo to begin.")

    # Private Chat Dashboard UI
    me = await client.get_me()
    first_name = message.from_user.first_name
    
    # Banner Image (Local File)
    banner_path = "banner.png" 
    
    caption = (
        f"Hey {first_name} 👋\n\n"
        "🎲 **This is LudoXBot!**\n"
        "A fast & fun multiplayer Ludo game for Telegram groups.\n\n"
        "➕ Add me to a group to start playing.\n"
        "📖 Use the menu below to explore features."
    )
    
    keyboard = InlineKeyboardMarkup([
        # Row 1: Add me to group
        [InlineKeyboardButton("✨ ADD ME TO YOUR GROUP ✨", url=f"https://t.me/{me.username}?startgroup=true")],
        # Row 2: Support & Owner
        [
            InlineKeyboardButton("SUPPORT", url="https://t.me/cosysx_community"),
            InlineKeyboardButton("❤️ OWNER ❤️", url="https://t.me/noneQ_0")
        ],
        # Row 3: Updates & Language
        [
            InlineKeyboardButton("UPDATES ♪", url="https://t.me/cosysx"),
            InlineKeyboardButton("🌐 LANGUAGE", callback_data="lang:menu")
        ],
        # Row 4: Help and Command
        [InlineKeyboardButton("♡ HELP AND COMMAND ♡", callback_data="help:menu")],
        # Row 5: Source
        [InlineKeyboardButton("✨ SOURCE ✨", url="https://github.com/example/ludo-bot")]
    ])
    
    try:
        await message.reply_photo(photo=banner_path, caption=caption, reply_markup=keyboard)
    except Exception as e:
        logger.error(f"Failed to send dashboard photo: {e}")
        # Fallback to text if photo fails
        await message.reply_text(caption, reply_markup=keyboard)

async def cmd_help(client, message):
    text = (
        "📖 **Ludo Bot Help**\n\n"
        "**Private Chat:**\n"
        "/start - Welcome info\n"
        "/credits - Your credits balance\n"
        "/ludorank - Global rankings\n"
        "/season - Season statistics\n\n"
        "**Groups:**\n"
        "/startludo - Create a new game lobby\n"
        "/join - Join a lobby or tournament\n"
        "/ludostate - Show current game board\n"
        "/ludostop - End current game (Admins)\n"
        "/ludotournament - Start a tournament"
    )
    await message.reply(text)

async def cmd_ludostop(client, message):
    # Only admins can stop the game in groups
    if message.chat.type in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
        member = await client.get_chat_member(message.chat.id, message.from_user.id)
        if member.status not in [enums.ChatMemberStatus.ADMINISTRATOR, enums.ChatMemberStatus.OWNER]:
            return await message.reply("Only admins can stop the game!")
    
    if manager.delete_game(message.chat.id):
        await message.reply("🛑 **Game stopped and lobby cleared by Admin.**")
    else:
        await message.reply("No active game to stop.")

async def cmd_ludostate(client, message):
    state = await manager.get_game_state(message.chat.id)
    if not state:
        return await message.reply("No active game in this chat. Use /startludo to begin!")
    
    if state.is_lobby:
        p_list = "\n".join([f"{i+1}. {p.first_name}" for i, p in enumerate(state.players)])
        await message.reply(f"🎮 **Ludo Lobby - Waiting for players**\n\n{p_list}")
    else:
        # Re-send the game board
        board_text = render_board(state)
        current_p = state.players[state.current_turn_index]
        text = f"🕹 **Current Game State**\nTurn: {COLORS[current_p.color_index]} **{current_p.first_name}**\n\n<code>{board_text}</code>"
        await message.reply(text, parse_mode=enums.ParseMode.HTML)

async def cmd_join(client, message):
    chat_id, user_id, user_name = message.chat.id, message.from_user.id, message.from_user.first_name
    msg = manager.join_lobby(chat_id, user_id, user_name)
    await message.reply(msg)

async def cmd_startludo(client, message):
    if message.chat.type not in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
        return await message.reply("This bot only works in groups!")
    err = manager.create_lobby(message.chat.id, message.from_user.id, message.from_user.first_name)
    if err: return await message.reply(err)
    text = f"🎮 **Ludo Lobby**\n\n1. {message.from_user.first_name}\n\n_Minimum 2 players to start._"
    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("➕ Join", callback_data="ludo:join"), InlineKeyboardButton("▶️ Start Game", callback_data="ludo:start")]])
    await message.reply(text, reply_markup=keyboard)

async def cmd_seasonalrank(client, message):
    s_id = await db.get_active_season_id()
    leaderboard = await db.get_leaderboard(season_id=s_id)
    if not leaderboard:
        return await message.reply(f"No rankings for Season {s_id} yet.")
    
    text = f"🌟 **Season {s_id} Rankings**\n\n"
    for i, (name, rating, wins) in enumerate(leaderboard, 1):
        medal = "🥇" if i == 1 else ("🥈" if i == 2 else ("🥉" if i == 3 else f"{i}."))
        text += f"{medal} **{name}**\n   Rating: `{rating}` | Wins: `{wins}`\n"
    await message.reply(text)

async def cmd_ludoseason(client, message):
    s_id = await db.get_active_season_id()
    await message.reply(f"📅 **Current Season:** {s_id}\nUse /seasonalrank to see the leaderboard!")

async def cmd_resetseason(client, message):
    # Admin only check (simple check for now)
    member = await client.get_chat_member(message.chat.id, message.from_user.id)
    if member.status not in [enums.ChatMemberStatus.ADMINISTRATOR, enums.ChatMemberStatus.OWNER]:
        return await message.reply("Only admins can reset the season.")
    
    await db.reset_season()
    new_id = await db.get_active_season_id()
    await message.reply(f"✅ Season reset! **New Season {new_id}** is now active.")

async def cmd_ludorank(client, message):
    leaderboard = await db.get_leaderboard()
    if not leaderboard:
        return await message.reply("No rankings available yet. Play a game to get ranked!")
    
    text = "🏆 **Global Ludo Rankings**\n\n"
    for i, (name, rating, wins) in enumerate(leaderboard, 1):
        medal = "🥇" if i == 1 else ("🥈" if i == 2 else ("🥉" if i == 3 else f"{i}."))
        text += f"{medal} **{name}**\n   Rating: `{rating}` | Wins: `{wins}`\n"
    await message.reply(text)

async def cmd_credits(client, message):
    balance = await db.get_credits(message.from_user.id)
    await message.reply(f"💰 **Your Balance:** `{balance} credits`")

async def cmd_tournament_lobby(client, message):
    t_id = t_manager.create_tournament(message.from_user.id)
    text = f"🏆 **Ludo Tournament Created!**\nTournament ID: `{t_id}`\n\nPlayers: 1/16\n1. {message.from_user.first_name}"
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Join", callback_data=f"tourney:join:{t_id}")],
        [InlineKeyboardButton("▶️ Start Tournament", callback_data=f"tourney:start:{t_id}")]
    ])
    await message.reply(text, reply_markup=keyboard)

# 7. CALLBACK HANDLER
async def handle_callback(client, query):
    data = query.data.split(":")
    logger.info(f"Callback received: {data}")
    if data[0] != "ludo": return
    
    action = data[1]
    # Data format: ludo:action:optional_val:optional_match_id
    # We need to be careful with indexing
    match_id = None
    if len(data) > 3: # ludo:move:v:m_abc
        match_id = data[3]
    elif len(data) > 2 and action in ["roll", "join", "start"]: # ludo:roll:m_abc
        match_id = data[2]

    chat_id, user_id, user_name = query.message.chat.id, query.from_user.id, query.from_user.first_name
    
    state = await manager.get_game_state(chat_id, match_id=match_id)
    if not state: 
        logger.warning(f"Game not found for callback: {chat_id} {match_id}")
        return await query.answer("Game not found.", show_alert=True)

    if action == "join":
        msg = manager.join_lobby(chat_id, user_id, user_name)
        await query.answer(msg)
        if "joined" in msg:
            p_list = "\n".join([f"{i+1}. {p.first_name}" for i, p in enumerate(state.players)])
            await query.edit_message_text(f"🎮 **Ludo Lobby**\n\n{p_list}", reply_markup=query.message.reply_markup)
            
    elif action == "start":
        # Only the first player (creator) can start
        if user_id != state.players[0].user_id:
            return await query.answer("Only the lobby creator can start the game.", show_alert=True)
        msg = manager.start_game(chat_id, user_id)
        if "started" in msg:
            await query.answer("Starting...")
            await refresh_game_view(query.message, state)
        else:
            await query.answer(msg, show_alert=True)
            
    elif action == "roll":
        val, msg = manager.roll_dice(chat_id, user_id, match_id=match_id)
        if val is not None:
            await query.answer(f"You rolled {val}!")
            await refresh_game_view(query.message, state)
        else:
            await query.answer(msg, show_alert=True)
            if "Skipping" in msg:
                await refresh_game_view(query.message, state)
                
    elif action == "move":
        token_id = int(data[2])
        msg = await manager.move_token(chat_id, user_id, token_id, match_id=match_id)
        await query.answer(msg)
        if "won" in msg:
            await query.edit_message_text(f"🏁 **GAME OVER**\n\n{msg}")
            # If match was part of a tournament
            if state and state.match_id and state.tournament_id:
                t_id = state.tournament_id
                t_manager.set_match_winner(t_id, state.match_id, user_id)
                
                t = t_manager.tournaments.get(t_id)
                if t:
                    if t.status == "finished":
                        await client.send_message(chat_id, f"🏆 **Tournament {t_id} Winner:** {user_name}!")
                    else:
                        # Check if a new round just started
                        current_round = t.rounds[-1]
                        if not any(m.winner for m in current_round):
                            # New round! Launch matches
                            await client.send_message(chat_id, f"📅 **Round {len(t.rounds)} of Tournament {t_id} is starting!**")
                            for m in current_round:
                                await launch_match(client, chat_id, m, t_id)
        else:
            await refresh_game_view(query.message, state)

async def handle_tourney_callback(client, query):
    data = query.data.split(":")
    action = data[1]
    t_id = data[2]
    user_id = query.from_user.id
    user_name = query.from_user.first_name
    
    t = t_manager.tournaments.get(t_id)
    if not t: return await query.answer("Tournament not found.")

    if action == "join":
        msg = t_manager.join_tournament(t_id, user_id)
        await query.answer(msg)
        if "successfully" in msg:
            p_names = []
            for uid in t.players:
                try:
                    u = await client.get_users(uid)
                    p_names.append(u.first_name)
                except: p_names.append("Unknown")
            p_list = "\n".join([f"{i+1}. {name}" for i, name in enumerate(p_names)])
            await query.edit_message_text(f"🏆 **Ludo Tournament**\nID: `{t_id}`\n\nPlayers: {len(t.players)}/16\n{p_list}", reply_markup=query.message.reply_markup)
            
    elif action == "start":
        if user_id != t.players[0]:
            return await query.answer("Only the creator can start.")
        err = t_manager.start_tournament(t_id)
        if err: return await query.answer(err, show_alert=True)
        
        await query.answer("Tournament Started!")
        await query.edit_message_text(f"🏆 **Tournament {t_id} is ACTIVE!**\nLaunching Round 1 matches...")
        
        # Launch matches
        round_1 = t.rounds[0]
        for match in round_1:
            await launch_match(client, query.message.chat.id, match, t_id)

async def handle_dashboard_callback(client, query):
    data = query.data
    
    if data == "help:menu":
        text = (
            "📖 **Ludo Bot - Help & How to Play**\n\n"
            "**How to Play:**\n"
            "1. Add the bot to a group.\n"
            "2. Send /startludo to create a lobby.\n"
            "3. Players join via the 'Join' button.\n"
            "4. The creator starts the game.\n\n"
            "**Commands:**\n"
            "• `/startludo` - Start a game\n"
            "• `/ludostate` - Check board status\n"
            "• `/ludorank` - Global rankings\n"
            "• `/credits` - Your balance\n\n"
            "**Game Rules:**\n"
            "• Roll a 6 to bring a token out.\n"
            "• Capturing an opponent gives an extra roll.\n"
            "• Reaching home gives an extra roll."
        )
        await query.edit_message_caption(caption=text, reply_markup=query.message.reply_markup)
        
    elif data == "lang:menu":
        text = (
            "🌐 **Language Selection**\n\n"
            "Please select your preferred language:\n"
            "(Currently only English is supported. More coming soon!)"
        )
        await query.answer("Language selection is under development.", show_alert=True)
        # We could also edit caption to show language buttons if implemented

# 8. MAIN STARTUP
async def run_bot():
    await db.init_db()
    app = Client("ludo_bot_session", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
    
    # Commands
    app.add_handler(MessageHandler(cmd_broadcast, filters.command("broadcast"))) # Admin only checked inside
    app.add_handler(MessageHandler(handle_broadcast_message, filters.text & ~filters.command(["broadcast", "start", "help"])), group=1)
    
    app.add_handler(MessageHandler(cmd_start, filters.command("start")))
    app.add_handler(MessageHandler(cmd_help, filters.command("help")))
    app.add_handler(MessageHandler(cmd_startludo, filters.command("startludo")))
    app.add_handler(MessageHandler(cmd_ludostop, filters.command(["ludostop", "stop"])))
    app.add_handler(MessageHandler(cmd_ludostate, filters.command("ludostate")))
    app.add_handler(MessageHandler(cmd_join, filters.command("join")))
    app.add_handler(MessageHandler(cmd_ludorank, filters.command("ludorank")))
    app.add_handler(MessageHandler(cmd_seasonalrank, filters.command("seasonalrank")))
    app.add_handler(MessageHandler(cmd_ludoseason, filters.command(["ludoseason", "season"])))
    app.add_handler(MessageHandler(cmd_resetseason, filters.command("resetseason")))
    app.add_handler(MessageHandler(cmd_credits, filters.command("credits")))
    app.add_handler(MessageHandler(cmd_tournament_lobby, filters.command(["ludotournament", "jointournament"])))
    
    # Tracking (Lowest priority, catches everything)
    app.add_handler(MessageHandler(track_chats, filters.all), group=-1)

    # Callbacks
    app.add_handler(CallbackQueryHandler(handle_callback, filters.regex("^ludo:")))
    app.add_handler(CallbackQueryHandler(handle_tourney_callback, filters.regex("^tourney:")))
    app.add_handler(CallbackQueryHandler(handle_dashboard_callback, filters.regex("^(help|lang):")))
    
    await app.start()
    
    # Register Scoped Commands (Must be done after app.start)
    try:
        await set_scoped_commands(app)
    except Exception as e:
        logger.error(f"Failed to set scoped commands: {e}")

    me = await app.get_me()
    logger.info(f"Bot @{me.username} is ONLINE")
    asyncio.create_task(timeout_checker())
    await idle()
    await app.stop()

if __name__ == "__main__":
    try:
        loop.run_until_complete(run_bot())
    except KeyboardInterrupt: pass
    except Exception as e: logger.critical(f"FATAL: {e}", exc_info=True)
