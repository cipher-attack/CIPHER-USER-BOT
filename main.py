import os
import asyncio
import logging
from telethon import TelegramClient, functions
from telethon.sessions import StringSession
from aiohttp import web

# 1. Logging ማስተካከል (ችግሩን እንድናይ ይረዳናል)
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# 2. መረጃዎችን መቀበል
api_id = os.environ.get("API_ID")
api_hash = os.environ.get("API_HASH")
session_string = os.environ.get("SESSION")

# መረጃዎቹ መኖራቸውን ማረጋገጥ
if not api_id or not api_hash or not session_string:
    logger.error("❌ Error: API_ID, API_HASH or SESSION variable is missing!")
    exit(1)

# ቁጥር መሆኑን ማረጋገጥ
try:
    api_id = int(api_id)
except ValueError:
    logger.error("❌ Error: API_ID must be a number!")
    exit(1)

# Telegram Client Setup
client = TelegramClient(StringSession(session_string), api_id, api_hash)

async def main():
    # A. ቴሌግራምን ማስጀመር
    logger.info("⏳ Connecting to Telegram servers...")
    try:
        await client.start()
        me = await client.get_me()
        logger.info(f"✅ SUCCESSFULLY LOGGED IN AS: {me.first_name} (ID: {me.id})")
    except Exception as e:
        logger.error(f"❌ FAILED TO CONNECT TO TELEGRAM: {e}")
        # ቴሌግራም ካልሰራ ሙሉ ፕሮግራሙ ይቁም
        return

    # B. Web Server ማስጀመር (Render እንዳይዘጋ)
    async def handle(request):
        return web.Response(text=f"Bot is running for {me.first_name}!")

    app = web.Application()
    app.router.add_get('/', handle)
    runner = web.AppRunner(app)
    await runner.setup()
    
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    logger.info(f"🚀 Web Server started on port {port}")

    # C. Online ማድረጊያ (Loop)
    logger.info("😎 Starting Keep-Online loop...")
    while True:
        try:
            await client(functions.account.UpdateStatus(offline=False))
            logger.info("ping sent - status: online")
            await asyncio.sleep(60)
        except Exception as e:
            logger.error(f"Error sending ping: {e}")
            await asyncio.sleep(10)

if __name__ == '__main__':
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        pass