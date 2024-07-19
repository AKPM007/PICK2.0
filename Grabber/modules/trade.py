from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from . import user_collection, app , collection 

pending_trades = {}

@app.on_message(filters.command("strade"))
async def trade(client, message):
    sender_id = message.from_user.id

    if not message.reply_to_message:
        await message.reply_text("You need to reply to a user's message to trade a character!")
        return

    receiver_id = message.reply_to_message.from_user.id

    if sender_id == receiver_id:
        await message.reply_text("You can't trade a character with yourself!")
        return

    if len(message.command) != 3:
        await message.reply_text("You need to provide two character IDs!")
        return

    sender_character_id, receiver_character_id = message.command[1], message.command[2]

    sender = await user_collection.find_one({'id': sender_id})
    receiver = await user_collection.find_one({'id': receiver_id})

    sender_character = next((character for character in sender['characters'] if character['id'] == sender_character_id), None)
    receiver_character = next((character for character in receiver['characters'] if character['id'] == receiver_character_id), None)

    if not sender_character:
        await message.reply_text("You don't have the character you're trying to trade!")
        return

    if not receiver_character:
        await message.reply_text("The other user doesn't have the character they're trying to trade!")
        return

    pending_trades[(sender_id, receiver_id)] = (sender_character_id, receiver_character_id)

    mention = f"[{message.reply_to_message.from_user.first_name}](tg://user?id={receiver_id})"
    keyboard = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("✅ Confirm Trade", callback_data=f"confirm_trade|{sender_id}|{receiver_id}")],
            [InlineKeyboardButton("❌ Cancel Trade", callback_data=f"cancel_trade|{sender_id}|{receiver_id}")]
        ]
    )

    await message.reply_text(f"{mention}, do you accept this trade?", reply_markup=keyboard, parse_mode='Markdown')

@app.on_callback_query(filters.regex(r"confirm_trade\|\d+\|\d+"))
async def confirm_trade(client, query):
    data = query.data.split("|")

    if len(data) != 3:
        await query.answer("Invalid trade request!", show_alert=True)
        return

    sender_id = int(data[1])
    receiver_id = int(data[2])

    if query.from_user.id != receiver_id:
        await query.answer("This trade request is not for you!", show_alert=True)
        return

    if (sender_id, receiver_id) not in pending_trades:
        await query.answer("This trade is not pending or already processed!", show_alert=True)
        return

    sender = await user_collection.find_one({'id': sender_id})
    receiver = await user_collection.find_one({'id': receiver_id})

    sender_character_id, receiver_character_id = pending_trades[(sender_id, receiver_id)]
    sender_character = next((character for character in sender['characters'] if character['id'] == sender_character_id), None)
    receiver_character = next((character for character in receiver['characters'] if character['id'] == receiver_character_id), None)

    if not sender_character or not receiver_character:
        await query.answer("One or both characters involved in the trade were not found!", show_alert=True)
        return

    sender['characters'].remove(sender_character)
    receiver['characters'].remove(receiver_character)

    receiver['characters'].append(sender_character)
    sender['characters'].append(receiver_character)

    await user_collection.update_one({'id': sender_id}, {'$set': {'characters': sender['characters']}})
    await user_collection.update_one({'id': receiver_id}, {'$set': {'characters': receiver['characters']}})

    del pending_trades[(sender_id, receiver_id)]

    mention = f"[{query.from_user.first_name}](tg://user?id={receiver_id})"
    await query.message.edit_text(f"🥳 Successfully traded characters with {mention}!", parse_mode='Markdown')

@app.on_callback_query(filters.regex(r"cancel_trade\|\d+\|\d+"))
async def cancel_trade(client, query):
    data = query.data.split("|")

    if len(data) != 3:
        await query.answer("Invalid trade request!", show_alert=True)
        return

    sender_id = int(data[1])
    receiver_id = int(data[2])

    if query.from_user.id != receiver_id:
        await query.answer("This trade request is not for you!", show_alert=True)
        return

    if (sender_id, receiver_id) not in pending_trades:
        await query.answer("This trade is not pending or already processed!", show_alert=True)
        return

    del pending_trades[(sender_id, receiver_id)]

    await query.message.edit_text("❌ Trade cancelled.")

