from pyrogram import types, enums
import os

async def send_dashboard(client, message):
    """Sends the premium dashboard UI in private chat."""
    user = message.from_user
    me = await client.get_me()
    bot_username = me.username
    
    caption = (
        f"Hey **{user.first_name}** 👋\n\n"
        "🎲 **This is LudoXBot!**\n"
        "A fast & fun multiplayer Ludo game for Telegram groups.\n\n"
        "➕ **Add me to a group to start playing.**\n"
        "📖 **Use the menu below to explore features.**"
    )
    
    keyboard = types.InlineKeyboardMarkup([
        [
            types.InlineKeyboardButton(
                "✨ ADD ME TO YOUR GROUP ✨",
                url=f"https://t.me/{bot_username}?startgroup=true"
            )
        ],
        [
            types.InlineKeyboardButton("SUPPORT", url="https://t.me/your_support"), # Placeholder
            types.InlineKeyboardButton("❤️ OWNER ❤️", url="https://t.me/your_owner")   # Placeholder
        ],
        [
            types.InlineKeyboardButton("UPDATES ♪", url="https://t.me/your_updates"), # Placeholder
            types.InlineKeyboardButton("🌐 LANGUAGE", callback_data="lang:menu")
        ],
        [
            types.InlineKeyboardButton("♡ HELP AND COMMAND ♡", callback_data="help:menu")
        ],
        [
            types.InlineKeyboardButton("✨ SOURCE ✨", url="https://github.com/your_source") # Placeholder
        ]
    ])
    
    # Check if banner exists, else send message only
    if os.path.exists("banner.png"):
        await message.reply_photo(
            photo="banner.png",
            caption=caption,
            reply_markup=keyboard
        )
    else:
        await message.reply(
            text=f"[📸] **LudoXBot**\n\n{caption}",
            reply_markup=keyboard
        )

async def help_menu_handler(client, callback_query):
    """Shows help menu via callback."""
    help_text = (
        "**📖 LudoXBot Help Menu**\n\n"
        "**Commands:**\n"
        "/ludo - Start a game (Groups)\n"
        "/staterank - Global wins/rank\n"
        "/seasoncredits - Your balance\n\n"
        "**How to Play:**\n"
        "1. Start in a group with /ludo.\n"
        "2. Players join using the button.\n"
        "3. Wait for 2-4 players.\n"
        "4. Move tokens to center home.\n\n"
        "**Safe Zones:** Stars 🌟 on board protect tokens from being killed."
    )
    # Using edit_message_caption if it was a photo, or edit_message_text if text
    if callback_query.message.photo:
        await callback_query.edit_message_caption(
            caption=help_text,
            reply_markup=types.InlineKeyboardMarkup([
                [types.InlineKeyboardButton("🔙 BACK", callback_data="menu:back")]
            ])
        )
    else:
        await callback_query.edit_message_text(
            text=help_text,
            reply_markup=types.InlineKeyboardMarkup([
                [types.InlineKeyboardButton("🔙 BACK", callback_data="menu:back")]
            ])
        )

async def lang_menu_handler(client, callback_query):
    """Shows language selection (stub)."""
    await callback_query.answer("Language selection is under development!", show_alert=True)

async def back_to_menu_handler(client, callback_query):
    """Goes back to home dashboard."""
    user = callback_query.from_user
    me = await client.get_me()
    bot_username = me.username
    
    caption = (
        f"Hey **{user.first_name}** 👋\n\n"
        "🎲 **This is LudoXBot!**\n"
        "A fast & fun multiplayer Ludo game for Telegram groups.\n\n"
        "➕ **Add me to a group to start playing.**\n"
        "📖 **Use the menu below to explore features.**"
    )
    
    keyboard = types.InlineKeyboardMarkup([
        [types.InlineKeyboardButton("✨ ADD ME TO YOUR GROUP ✨", url=f"https://t.me/{bot_username}?startgroup=true")],
        [types.InlineKeyboardButton("SUPPORT", url="https://t.me/your_support"), types.InlineKeyboardButton("❤️ OWNER ❤️", url="https://t.me/your_owner")],
        [types.InlineKeyboardButton("UPDATES ♪", url="https://t.me/your_updates"), types.InlineKeyboardButton("🌐 LANGUAGE", callback_data="lang:menu")],
        [types.InlineKeyboardButton("♡ HELP AND COMMAND ♡", callback_data="help:menu")],
        [types.InlineKeyboardButton("✨ SOURCE ✨", url="https://github.com/your_source")]
    ])
    
    if callback_query.message.photo:
        await callback_query.edit_message_caption(caption=caption, reply_markup=keyboard)
    else:
        await callback_query.edit_message_text(text=caption, reply_markup=keyboard)
