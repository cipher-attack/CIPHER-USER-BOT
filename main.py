from telethon import TelegramClient, functions
import asyncio
import os  # ይህን መጨመር አለብህ

# ቁጥሩን እዚህ አትጻፍ! ከሰርቨሩ እንዲጠራ እዘዘው፡
api_id = int(os.environ.get("API_ID"))
api_hash = os.environ.get("API_HASH")

# እዚህ ጋር ስልክ ቁጥር መጠየቅ እንዳይኖር String Session መጠቀም ይመረጣል (ከታች አብራራዋለሁ)
# ለጊዜው ግን እንደነበረ ይቆይ
client = TelegramClient('anon_session', api_id, api_hash)

async def keep_online():
    print("ስክሪፕቱ ጀምሯል...")
    while True:
        try:
            await client(functions.account.UpdateStatus(offline=False))
            await asyncio.sleep(60)
        except Exception as e:
            print(f"Error: {e}")
            await asyncio.sleep(10)

with client:
    client.loop.run_until_complete(keep_online())
