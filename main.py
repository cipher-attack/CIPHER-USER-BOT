from telethon import TelegramClient, functions
from telethon.sessions import StringSession
import asyncio
import os
from aiohttp import web

# መረጃዎችን ከ Environment Variables መቀበል
api_id = int(os.environ.get("API_ID"))
api_hash = os.environ.get("API_HASH")
session_string = os.environ.get("SESSION")

client = TelegramClient(StringSession(session_string), api_id, api_hash)

# 1. ቦቱን Online የሚያደርገው ክፍል
async def keep_online():
    print("Telegram Status: ONLINE")
    while True:
        try:
            await client(functions.account.UpdateStatus(offline=False))
            await asyncio.sleep(60)
        except Exception as e:
            print(f"Error: {e}")
            await asyncio.sleep(10)

# 2. Render እንዳይተኛ የሚጠብቀው (Dummy Web Server)
async def web_server(request):
    return web.Response(text="I am Alive!")

async def start_server():
    app = web.Application()
    app.router.add_get('/', web_server)
    runner = web.AppRunner(app)
    await runner.setup()
    # Render የሚሰጠውን PORT መጠቀም አለብን
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    print(f"Web Server started on port {port}")

# 3. ሁለቱን በአንድ ላይ ማሮጫ
async def main():
    await client.start()
    # ሁለቱንም ስራዎች (Telegram እና Web Server) በአንድ ላይ ያሮጣል
    await asyncio.gather(keep_online(), start_server())

if __name__ == '__main__':
    client.loop.run_until_complete(main())