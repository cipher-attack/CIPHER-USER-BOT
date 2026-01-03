from telethon import TelegramClient, functions
from telethon.sessions import StringSession
import asyncio
import os

# መረጃዎችን ከ Render Environment Variables ላይ ይቀበላል
api_id = int(os.environ.get("API_ID"))
api_hash = os.environ.get("API_HASH")
session_string = os.environ.get("SESSION")

# አሁን ስልክ ቁጥር አይጠይቅም፣ ቀጥታ በ Session ይገባል
client = TelegramClient(StringSession(session_string), api_id, api_hash)

async def keep_online():
    print("ስክሪፕቱ በስኬት ጀምሯል! አሁን Online ነህ።")
    while True:
        try:
            await client(functions.account.UpdateStatus(offline=False))
            # በየ 60 ሰከንዱ status ያድሳል
            await asyncio.sleep(60)
        except Exception as e:
            print(f"Error: {e}")
            await asyncio.sleep(10)

with client:
    client.loop.run_until_complete(keep_online())