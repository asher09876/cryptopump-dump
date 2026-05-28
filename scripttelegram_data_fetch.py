import asyncio
import json
import os
from datetime import datetime, timezone
from typing import List
from telethon import TelegramClient, errors
from telethon.tl.types import MessageMediaPhoto
import sys
from pathlib import Path

# Add parent directory to path to import config
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from config import (
    TELEGRAM_API_ID,
    TELEGRAM_API_HASH,
    TELEGRAM_PHONE_NUMBER,
    TELEGRAM_SESSION_NAME,
    TELEGRAM_CHANNELS,
    TELEGRAM_DATE_FROM,
    TELEGRAM_DATE_TO,
    TELEGRAM_MESSAGES_JSONL,
    TELEGRAM_IMAGES_DIR,
    ensure_directories,
)

async def _download_channel_messages(
    client: TelegramClient,
    channel: str,
    messages_file,
    fetch_timestamp: str,
):
    
    print(f"\n[+] Fetching from channel: {channel}")
    try:
        entity = await client.get_entity(channel)
    except Exception as e:
        print(f"[!] Failed to get entity for {channel}: {e}")
        return

    total_saved = 0
    async for message in client.iter_messages(
        entity,
        offset_date=TELEGRAM_DATE_TO,
        reverse=False  # newest -> oldest
    ):
        msg_date = message.date
        if msg_date.tzinfo is None:
            msg_date = msg_date.replace(tzinfo=timezone.utc)
       
        # Stop if we go past the lower bound
        if msg_date < TELEGRAM_DATE_FROM:
            break

        # Filter only within range
        if not (TELEGRAM_DATE_FROM <= msg_date <= TELEGRAM_DATE_TO):
            continue

        # Base record
        record = {
            "channel": channel,
            "message_id": message.id,
            "date": message.date.isoformat(),
            "fetch_timestamp": fetch_timestamp,
            "from_id": getattr(message.from_id, "user_id", None) if message.from_id else None,
            "text": message.message or "",
            "reply_to_msg_id": message.reply_to_msg_id,
            "views": getattr(message, "views", None),
            "forwards": getattr(message, "forwards", None),
            "image_path": None,
        }

        # If message contains a photo
        if isinstance(message.media, MessageMediaPhoto) or message.photo:
            img_filename = f"{channel}_{message.id}.jpg"
            img_path = os.path.join(TELEGRAM_IMAGES_DIR, img_filename)
            # Download photo
            try:
                await client.download_media(message, file=img_path)
                record["image_path"] = img_path
            except Exception as e:
                print(f"[!] Failed to download image for message {message.id} in {channel}: {e}")

        # Write JSON line
        messages_file.write(json.dumps(record, ensure_ascii=False) + "\n")
        total_saved += 1
        if total_saved % 100 == 0:
            print(f" Saved {total_saved} messages from {channel}...")

    print(f"[+] Finished {channel}: {total_saved} messages saved.")

async def main():
    ensure_directories()

    if TELEGRAM_API_ID == 123456 or TELEGRAM_API_HASH == "YOUR_API_HASH_HERE":
        raise ValueError("Please set TELEGRAM_API_ID and TELEGRAM_API_HASH in config.py or environment variables.")

    # Capture fetch timestamp
    fetch_timestamp = datetime.now(timezone.utc).isoformat()

    client = TelegramClient(
        TELEGRAM_SESSION_NAME,
        TELEGRAM_API_ID,
        TELEGRAM_API_HASH,
    )

    # session is stored locally (no otp)
    await client.start(phone=TELEGRAM_PHONE_NUMBER)
    print("[+] Telegram client started. Session file created (for OTP-free future runs).")

    # Open file in append mode (can rerun or add channels later)
    with open(TELEGRAM_MESSAGES_JSONL, "a", encoding="utf-8") as f_out:
        for channel in TELEGRAM_CHANNELS:
            try:
                await _download_channel_messages(client, channel, f_out, fetch_timestamp)
            except errors.FloodWaitError as e:
                # In case of Telegram rate limits
                print(f"[!] FloodWaitError: need to wait {e.seconds} seconds. Skipping channel {channel} for now.")
            except Exception as e:
                print(f"[!] Unexpected error for channel {channel}: {e}")

    await client.disconnect()
    print("[+] Done. Client disconnected.")

if __name__ == "__main__":
    asyncio.run(main())
