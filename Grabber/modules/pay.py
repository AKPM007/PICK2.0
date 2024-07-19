import math
from pyrogram import Client, filters
from Grabber import application, user_collection
from pyrogram.types import Message
from datetime import datetime, timedelta
import asyncio
from . import add, deduct, show, app

last_payment_times = {}
last_loan_times = {}

def format_timedelta(td: timedelta) -> str:
    seconds = td.total_seconds()
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return "{:02}h {:02}m {:02}s".format(int(hours), int(minutes), int(seconds))

@app.on_message(filters.command('pay'))
async def mpay(client, message):
    sender_id = message.from_user.id

    if not message.reply_to_message:
        await message.reply_text("Please reply to a user to /pay.")
        return

    recipient_id = message.reply_to_message.from_user.id

    if sender_id == recipient_id:
        await message.reply_text("You can't pay yourself.")
        return

    try:
        amount = int(message.text.split()[1])
        if amount <= 0:
            raise ValueError("Amount must be greater than zero.")
    except (IndexError, ValueError):
        await message.reply_text("Invalid amount. Please provide a valid positive amount.")
        return

    sender_balance = await show(sender_id)
    if not sender_balance or sender_balance < amount:
        await message.reply_text("Insufficient balance to make the payment.")
        return

    last_payment_time = last_payment_times.get(sender_id)
    if last_payment_time:
        time_since_last_payment = datetime.now() - last_payment_time
        if time_since_last_payment < timedelta(minutes=10):
            cooldown_time = timedelta(minutes=10) - time_since_last_payment
            formatted_cooldown = format_timedelta(cooldown_time)
            await message.reply_text(f"Cooldown! You can pay again in {formatted_cooldown}.")
            return

    await deduct(sender_id, amount)
    await add(recipient_id, amount)

    last_payment_times[sender_id] = datetime.now()

    await client.send_message(
        message.chat.id,
        f"Payment Successful! You Paid Ŧ{amount} Tokens to {message.reply_to_message.from_user.username}."
    )