from telethon import TelegramClient, functions
from telethon.sessions import StringSession
import asyncio
import os
from aiohttp import web

# መረጃዎችን ከ Environment Variables ይቀበላል
api_id = int(os.environ.get("API_ID"))
api_hash = os.environ.get("API_HASH")
session_string = os.environ.get("SESSION")

# Telegram Client Setup
client = TelegramClient(StringSession(session_string), api_id, api_hash)

async def keep_online():
    """ይህ ፈንክሽን በየደቂቃው ለቴሌግራም 'Online ነኝ' ይላል"""
    print("✅ Telegram Loop Started! Ping sending...") 
    while True:
        try:
            # Online መሆኑን ማረጋገጫ
            await client(functions.account.UpdateStatus(offline=False))
            print("Ping sent to Telegram server (Still Online)")
            await asyncio.sleep(60)
        except Exception as e:
            print(f"❌ Error in keep_online: {e}")
            await asyncio.sleep(10)

async def web_server(request):
    """Render እንዳይተኛ የሚከላከል"""
    return web.Response(text="Bot is Running!")

async def start_services():
    # 1. መጀመሪያ ቴሌግራምን እናስጀምር
    print("⏳ Connecting to Telegram...")
    try:
        await client.start()
        print("✅ Telegram Connected Successfully!")
        
        # የራሴን መረጃ (Me) አምጣ - በትክክለኛው አካውንት መግባትህን ለማረጋገጥ
        me = await client.get_me()
        print(f"✅ Logged in as: {me.first_name} (ID: {me.id})")
        
        # Online ማድረጊያውን በ Background እናስጀምር
        asyncio.create_task(keep_online())
        
    except Exception as e:
        print(f"❌ Failed to connect to Telegram: {e}")
        return

    # 2. ቀጥሎ Web Server እናስጀምር
    app = web.Application()
    app.router.add_get('/', web_server)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, '0.0.0.0', port)
    
    print(f"🚀 Web Server started on port {port}")
    await site.start()
    
    # ኮዱ እንዳይዘጋ ይዞ ያቆየዋል
    while True:
        await asyncio.sleep(3600)

if __name__ == '__main__':
    # ዋናውን Loop ማስጀመሪያ
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(start_services())
    except KeyboardInterrupt:
        pass