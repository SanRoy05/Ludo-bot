from pyrogram import types
from db import db

async def help_handler(client, message):
    help_text = (
        "**🎲 Ludo Bot Help**\n\n"
        "**Commands:**\n"
        "/ludo - Start a new game lobby in a group\n"
        "/staterank - View your stats and global rank\n"
        "/seasoncredits - View your current credits\n"
        "/help - Show this message\n\n"
        "**How to Play:**\n"
        "1. Start a game with /ludo.\n"
        "2. Players join the lobby.\n"
        "3. Start the game when ready.\n"
        "4. Roll the dice and move your tokens.\n"
        "5. Reach the center to finish!\n\n"
        "**2v2 Team Mode:**\n"
        "Red + Yellow vs Green + Blue.\n"
        "Teammates can't kill each other and share victory!"
    )
    await message.reply(help_text)

async def stats_handler(client, message):
    user_id = message.from_user.id
    stats = await db.get_user_stats(user_id)
    
    if not stats:
        return await message.reply("You haven't played any games yet!")
        
    text = (
        f"**📊 Stats for @{stats['username']}**\n\n"
        f"🏆 **Wins:** {stats['wins']}\n"
        f"🎮 **Matches:** {stats['matches']}\n"
        f"💳 **Credits:** {stats['credits']}\n"
        f"🌍 **Global Rank:** #{stats['rank']}"
    )
    await message.reply(text)

async def credits_handler(client, message):
    user_id = message.from_user.id
    stats = await db.get_user_stats(user_id)
    
    if not stats:
        return await message.reply("You have 1000 starting credits! Start playing to earn more.")
        
    text = f"**💳 Your Season Credits:** {stats['credits']}"
    await message.reply(text)
