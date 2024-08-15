from pyrogram import filters, types as t
import random
import time
import asyncio
from pyrogram import Client
from Grabber import application, user_collection
from . import add, deduct, show

cooldown_duration_roll = 30
last_usage_time_roll = {}

@bot.on_message(filters.command(["basket"]))
async def roll_dart(_: bot, message: t.Message):
    user_id = message.from_user.id
    current_time = time.time()

    if not await user_collection.find_one({'id': user_id}):
        await message.reply("You need to grab some slave first.")
        return

    if user_id in last_usage_time_roll:
        time_elapsed = current_time - last_usage_time_roll[user_id]
        remaining_time = max(0, cooldown_duration_roll - time_elapsed)
        if remaining_time > 0:
            return await message.reply_text(f"You're on cooldown. Please wait {int(remaining_time)} seconds.")

    command_parts = message.text.split()
    if len(command_parts) != 2:
        return await message.reply_text("Invalid command.\nUsage: /basket 10000")

    try:
        bastek_amount = int(command_parts[1])
    except ValueError:
        return await message.reply_text("Invalid amount.")

    bal = await show(user_id)
    if bal is None:
        return await message.reply_text("You don't have enough cash to place this bet.")

    if bastek_amount > bal:
        return await message.reply_text("Insufficient balance to place this bet.")

    min_bet_amount = int(bal * 0.07)
    if bastek_amount < min_bet_amount:
        return await message.reply_text(f"Please bet at least 7% of your balance, which is â‚©{min_bet_amount}.")

    value = await bot.send_dice(chat_id=message.chat.id, emoji="🎯")

    await asyncio.sleep(2)
    if value.dice.value in [4, 5, 6]:
        await add(user_id, bastek_amount)
        await message.reply_text(f"[🎰](https://graph.org//file/5a2360e5023e2976eb23c.jpg) You're lucky!\nYou won â‚©{bastek_amount}")
        await add_xp(user_id, 4)
    else:
        await deduct(user_id, bastek_amount)
        await message.reply_text(f"[🍷](https://graph.org//file/5a2360e5023e2976eb23c.jpg) Better luck next time!\nYou lost â‚©{bastek_amount}")
        await deduct_xp(user_id, 2)

    last_usage_time_roll[user_id] = current_time

async def add_xp(user_id, xp_amount):
    await user_collection.update_one({'id': user_id}, {'$inc': {'xp': xp_amount}}, upsert=True)

async def deduct_xp(user_id, xp_amount):
    await user_collection.update_one({'id': user_id}, {'$inc': {'xp': -xp_amount}}, upsert=True)
