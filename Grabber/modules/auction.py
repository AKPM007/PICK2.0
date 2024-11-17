import asyncio
from datetime import datetime, timedelta
import random
from pyrogram import Client, filters
from pyrogram.types import Message
from . import user_collection, collection, app, capsify, nopvt
from .block import block_dec
from .watchers import auction_watcher

AUCTION_TIME = 60
MIN_BID = 10000
active_auctions = {}
message_counts = {}

async def start_auction(chat_id, character):
    character_id = str(character['id'])

    if character_id in active_auctions:
        return

    active_auctions[character_id] = {
        'character': character,
        'highest_bid': MIN_BID,
        'highest_bidder': None,
        'end_time': datetime.now() + timedelta(seconds=AUCTION_TIME),
    }

    await app.send_photo(
        chat_id=chat_id,
        photo=character['img_url'],
        caption=capsify(
            f"**Auction started for {character['name']}**\n"
            f"Anime: {character['anime']}\n"
            f"Rarity: {character['rarity']}\n\n"
            f"Place your bid using /bid amount\n"
            f"Minimum bid: {MIN_BID} rubies\n"
            f"Auction ends in {AUCTION_TIME} seconds!"
        )
    )

    message_counts[chat_id] = 0

    await asyncio.sleep(AUCTION_TIME)

    auction = active_auctions.get(character_id)
    if auction and auction['highest_bidder']:
        winner_id = auction['highest_bidder']
        winner_data = await user_collection.find_one({'id': winner_id})

        await user_collection.update_one(
            {'id': winner_id},
            {'$push': {'characters': character}},
            upsert=True
        )

        await app.send_message(
            chat_id=chat_id,
            text=capsify(
                f"**Auction Over!**\n\n"
                f"**{winner_data['first_name']}** won the auction for **{character['name']}** with a bid of {auction['highest_bid']} rubies!"
            )
        )
    else:
        await app.send_message(
            chat_id=chat_id,
            text=capsify(f"**Auction Over!**\n\nNo winner for {character['name']} as no bids were placed.")
        )

    del active_auctions[character_id]


@app.on_message(filters.text, group=auction_watcher)  
async def handle_message(client, message: Message):
    chat_id = message.chat.id
    message_counts.setdefault(chat_id, 0)
    message_counts[chat_id] += 1

    if message_counts[chat_id] >= 200:
        rarity_filter = {"rarity": {"$in": ["💋 Aura", "❄️ Winter"]}}
        characters = await collection.find(rarity_filter).to_list(None)

        if characters:
            character = random.choice(characters)
            await start_auction(chat_id, character)

        message_counts[chat_id] = 0


@app.on_message(filters.command("bid"))
@block_dec
@nopvt
async def place_bid(client, message: Message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    args = message.text.split()
    if len(args) < 2:
        await message.reply_text(capsify("Please provide a bid amount."))
        return

    try:
        bid_amount = int(args[1])
    except ValueError:
        await message.reply_text(capsify("Bid amount must be a number."))
        return

    if bid_amount < MIN_BID:
        await message.reply_text(capsify(f"The minimum bid is {MIN_BID} rubies."))
        return

    active_auction = None
    for auction in active_auctions.values():
        if auction['end_time'] > datetime.now():
            active_auction = auction
            break

    if not active_auction:
        await message.reply_text(capsify("No active auctions at the moment."))
        return

    user_data = await user_collection.find_one({'id': user_id})
    if not user_data or user_data.get('rubies', 0) < bid_amount:
        await message.reply_text(capsify("You do not have enough rubies to place this bid."))
        return

    if bid_amount > active_auction['highest_bid']:
        active_auction['highest_bid'] = bid_amount
        active_auction['highest_bidder'] = user_id

        await user_collection.update_one(
            {'id': user_id},
            {'$inc': {'rubies': -bid_amount}},
            upsert=True
        )

        await client.send_message(
            chat_id=chat_id,
            text=capsify(
                f"**{message.from_user.first_name}** bid {bid_amount} rubies on **{active_auction['character']['name']}**.\n"
                f"Time left: {max(0, (active_auction['end_time'] - datetime.now()).seconds)} seconds.\n"
                f"Current highest bid: {bid_amount} rubies."
            )
        )
    else:
        await message.reply_text(capsify("Your bid is lower than the current highest bid. Try again."))