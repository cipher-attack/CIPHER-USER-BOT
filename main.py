import os
import asyncio
import logging
from telethon import TelegramClient, events, functions
from telethon.sessions import StringSession
from aiohttp import web

# Logging Setup
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Credentials
api_id = os.environ.get("API_ID")
api_hash = os.environ.get("API_HASH")
session_string = os.environ.get("SESSION")

if not api_id or not api_hash or not session_string:
    logger.error("❌ Credentials missing!")
    exit(1)

client = TelegramClient(StringSession(session_string), int(api_id), api_hash)

# ---------------------------------------------------------
# 1. GHOST MODE & ANTI-DELETE (ሚስጥራዊው ክፍል)
# ---------------------------------------------------------

# ሰው መልእክት ሲልክልህ (ወደ Saved Messages ገልብጠው)
@client.on(events.NewMessage(incoming=True, func=lambda e: e.is_private))
async def incoming_handler(event):
    try:
        sender = await event.get_sender()
        sender_id = sender.id
        name = sender.first_name
        
        # ወደ Saved Messages እንልከዋለን (ከሰውዬው መረጃ ጋር)
        # እዚህ ጋር የምንጠቀመው ዘዴ: መልእክቱን Forward እናደርገዋለን
        # Forward ከተደረገ፣ Reply ስናደርግለት ወደማን እንደሚሄድ ቦቱ ያውቃል
        await client.forward_messages("me", event.message)
        
    except Exception as e:
        logger.error(f"Error handling incoming msg: {e}")

# አንተ Saved Messages ላይ ሆነህ Reply ስታደርግ (ወደ ሰውዬው ይሂድ)
@client.on(events.NewMessage(outgoing=True, chats="me"))
async def reply_handler(event):
    try:
        # Reply ካልሆነ ዝለለው
        if not event.is_reply:
            return

        # Reply የተደረገበትን ኦሪጅናል መልእክት እናምጣ
        reply_msg = await event.get_reply_message()
        
        # ያ መልእክት Forward የተደረገ ከሆነ (ከሰው የመጣ ከሆነ)
        if reply_msg.fwd_from:
            target_id = reply_msg.fwd_from.from_id
            
            # User ID ከሆነ ብቻ (Channel/Group ካልሆነ)
            if hasattr(target_id, 'user_id'):
                final_target = target_id.user_id
                
                # ለሰውዬው መልእክቱን እንላክለት (እንደ እኛ ሆኖ)
                await client.send_message(final_target, event.message.text)
                
                # ምልክት እንዲሆነን Saved Messages ላይ ራሱ edit እናድርገው
                await event.edit(f"✅ **Sent:** {event.message.text}")
                
    except Exception as e:
        logger.error(f"Error handling reply: {e}")

# ---------------------------------------------------------
# 2. SYSTEM KEEP ALIVE (እንደተለመደው)
# ---------------------------------------------------------

async def main():
    logger.info("⏳ Connecting...")
    await client.start()
    me = await client.get_me()
    logger.info(f"✅ GHOST MODE ACTIVATED FOR: {me.first_name}")

    # Web Server
    async def handle(request):
        return web.Response(text="Ghost Bot Running!")
    app = web.Application()
    app.router.add_get('/', handle)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()

    # Online Loop
    while True:
        try:
            await client(functions.account.UpdateStatusRequest(offline=False))
            await asyncio.sleep(60)
        except:
            await asyncio.sleep(10)

if __name__ == '__main__':
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(main())