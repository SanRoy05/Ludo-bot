import random
import asyncio
from pyrogram import types
from db import db
from board_renderer import render_board
from dice_renderer import generate_dice_frame
from game_logic import move_token, get_killing_impact
from team_logic import check_team_victory
from config import COLORS

async def send_board(client, chat_id, message_id=None):
    game = await db.get_game(chat_id)
    if not game: return
    
    img_buf = render_board(game)
    curr_player = game['players'][game['current_turn_index']]
    
    caption = f"**Ludo Game**\nTurn: {COLORS[curr_player['color']]} @{curr_player['username']}\n"
    if game['dice_value'] > 0:
        caption += f"Dice: 🎲 {game['dice_value']}"
        
    keyboard = []
    # If dice not rolled
    if game['dice_value'] == 0:
        keyboard.append([types.InlineKeyboardButton("🎲 Roll Dice", callback_data="roll")])
        keyboard.append([types.InlineKeyboardButton("🛑 Stop Game", callback_data="stop")])
    else:
        # Move buttons for available tokens
        row = []
        for i, t in enumerate(curr_player['tokens']):
            if t['position'] == 99: continue
            # Basic validation: can move or need 6 to exit
            if t['position'] == -1 and game['dice_value'] != 6: continue
            
            row.append(types.InlineKeyboardButton(f"Token {i+1}", callback_data=f"move_{i}"))
        
        if row:
            keyboard.append(row)
        else:
            keyboard.append([types.InlineKeyboardButton("Skip Turn (No Moves)", callback_data="skip")])
        
        keyboard.append([types.InlineKeyboardButton("🛑 Stop Game", callback_data="stop")])

    reply_markup = types.InlineKeyboardMarkup(keyboard)
    
    if message_id:
        try:
            await client.edit_message_media(
                chat_id, message_id,
                media=types.InputMediaPhoto(img_buf, caption=caption),
                reply_markup=reply_markup
            )
        except:
            # Fallback if edit fails (e.g. same content)
            pass
    else:
        await client.send_photo(chat_id, photo=img_buf, caption=caption, reply_markup=reply_markup)

async def roll_handler(client, callback_query):
    chat_id = callback_query.message.chat.id
    game = await db.get_game(chat_id)
    
    curr_player = game['players'][game['current_turn_index']]
    if callback_query.from_user.id != curr_player['user_id']:
        return await callback_query.answer("It's not your turn!", show_alert=True)
        
    if game['dice_value'] != 0:
        return await callback_query.answer("Dice already rolled!")

    # Dice Animation (2 frames for stability)
    for _ in range(2):
        fake_val = random.randint(1, 6)
        frame = generate_dice_frame(fake_val)
        try:
            await client.edit_message_media(
                chat_id, callback_query.message.id,
                media=types.InputMediaPhoto(frame, caption="🎲 Rolling...")
            )
            await asyncio.sleep(0.4)
        except Exception:
            break

    real_val = random.randint(1, 6)
    
    # Track consecutive 6s
    consecutive_sixes = game.get('consecutive_sixes', 0)
    if real_val == 6:
        consecutive_sixes += 1
    else:
        consecutive_sixes = 0
    
    await db.update_game_state(game['id'], dice_value=real_val, consecutive_sixes=consecutive_sixes)
    
    # Three 6s Rule: Turn immediately ends after third consecutive 6
    if consecutive_sixes >= 3:
        await callback_query.answer(f"You rolled your 3rd consecutive 6! Turn ended.", show_alert=True)
        await asyncio.sleep(1.5)
        # Reset consecutive 6s and skip turn
        await db.update_game_state(game['id'], consecutive_sixes=0)
        await skip_turn(game)
        await send_board(client, chat_id, callback_query.message.id)
        return
    
    # Check if any moves possible
    any_possible = False
    for t in curr_player['tokens']:
        if t['position'] == -1 and real_val == 6: 
            any_possible = True
        elif 0 <= t['position'] <= 51:
            # Check if move stays within bounds
            any_possible = True
        elif 52 <= t['position'] <= 57:
            # Check if can move in home stretch
            if t['position'] + real_val <= 58:
                any_possible = True
            
    if not any_possible:
        # Auto-skip if no moves
        await callback_query.answer(f"You rolled {real_val}, but no moves possible!", show_alert=True)
        await asyncio.sleep(1)
        # Reset consecutive 6s when turn ends
        await db.update_game_state(game['id'], consecutive_sixes=0)
        await skip_turn(game)
        await send_board(client, chat_id, callback_query.message.id)
    else:
        await send_board(client, chat_id, callback_query.message.id)

async def move_handler(client, callback_query, token_idx):
    chat_id = callback_query.message.chat.id
    game = await db.get_game(chat_id)
    
    curr_player = game['players'][game['current_turn_index']]
    if callback_query.from_user.id != curr_player['user_id']:
        return await callback_query.answer("Not your turn!")
        
    dice_val = game['dice_value']
    if dice_val == 0:
        return await callback_query.answer("Roll the dice first!")

    new_pos, finished = move_token(curr_player, token_idx, dice_val)
    if new_pos == curr_player['tokens'][token_idx]['position']:
        return await callback_query.answer("Invalid move for this token.")

    # Update Token
    await db.update_token(curr_player['tokens'][token_idx]['id'], new_pos, finished)
    
    # Killing logic
    killing_impact = get_killing_impact(game, curr_player['color'], new_pos)
    for p_idx, t_idx in killing_impact:
        victim_token_id = game['players'][p_idx]['tokens'][t_idx]['id']
        await db.update_token(victim_token_id, -1, False)

    # Check Victory
    # Need to fetch fresh state for victory check
    game = await db.get_game(chat_id)
    winner_team = check_team_victory(game) if game['team_mode'] else None
    
    # Simplified solo victory check if not team mode
    if not game['team_mode']:
        if all(t['position'] == 99 for t in curr_player['tokens']):
            await callback_query.message.reply(f"🎉 @{curr_player['username']} HAS WON!")
            # Update winner stats
            await db.update_user_stats(curr_player['user_id'], curr_player['username'], won=True)
            # Update other players stats
            for p in game['players']:
                if p['user_id'] != curr_player['user_id']:
                    await db.update_user_stats(p['user_id'], p['username'], won=False)
            
            await db.close_game(chat_id)
            return

    if winner_team:
        await callback_query.message.reply(f"🏆 TEAM {winner_team} HAS WON!")
        # Update stats for all players
        for p in game['players']:
            is_winner = (p['team_id'] == winner_team)
            await db.update_user_stats(p['user_id'], p['username'], won=is_winner)
            
        await db.close_game(chat_id)
        return

    # Turn management
    # Extra turn on 6 or kill
    if dice_val == 6 or killing_impact:
        await db.update_game_state(game['id'], dice_value=0)
    else:
        await skip_turn(game)
        
    await send_board(client, chat_id, callback_query.message.id)

async def skip_turn(game):
    next_turn = (game['current_turn_index'] + 1) % len(game['players'])
    await db.update_game_state(game['id'], current_turn_index=next_turn, dice_value=0, consecutive_sixes=0)

async def stop_game_handler(client, update):
    is_callback = hasattr(update, "data")
    message = update.message if is_callback else update
    chat_id = message.chat.id
    user = update.from_user
    
    game = await db.get_game(chat_id)
    if not game:
        if is_callback: await update.answer("Game already closed.")
        else: await message.reply("No active game to stop.")
        return
    
    # Check if user is a participant
    if not any(p['user_id'] == user.id for p in game['players']):
        if is_callback: await update.answer("Only players can stop the game!", show_alert=True)
        else: await message.reply("Only players can stop the game!")
        return

    await db.close_game(chat_id)
    
    stop_text = f"🛑 **Game Stopped** by @{user.username or user.first_name}"
    
    if is_callback:
        await message.edit_caption(stop_text)
        await update.answer("Game has been stopped.")
    else:
        await message.reply(stop_text)
