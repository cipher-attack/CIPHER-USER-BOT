import os
import asyncio
import logging
from telethon import TelegramClient, events, functions, types
from telethon.sessions import StringSession
from aiohttp import web
from deep_translator import GoogleTranslator

# ---------------------------------------------------------
# 1. SETUP & CONFIGURATION
# ---------------------------------------------------------

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

api_id = os.environ.get("API_ID")
api_hash = os.environ.get("API_HASH")
session_string = os.environ.get("SESSION")
app_url = os.environ.get("RENDER_EXTERNAL_URL", "http://0.0.0.0:8080")

if not api_id or not api_hash or not session_string:
    logger.error("❌ Error: Credentials missing!")
    exit(1)

try:
    client = TelegramClient(StringSession(session_string), int(api_id), api_hash)
except Exception as e:
    logger.error(f"❌ Init Error: {e}")
    exit(1)

# Cache: ID የደበቁ ሰዎችን መልእክት የምናስታውስበት
# Format: {Saved_Message_ID : Original_Sender_ID}
reply_cache = {}
download_cache = {}

# ---------------------------------------------------------
# 2. PREMIUM FEATURES
# ---------------------------------------------------------

# A. TRANSLATOR
@client.on(events.NewMessage(outgoing=True, pattern=r"^\.tr"))
async def translate_reply(event):
    reply = await event.get_reply_message()
    if not reply or not reply.text:
        await event.edit("❌ Reply to text!")
        return
    try:
        await event.edit("🔄 **Translating...**")
        translation = GoogleTranslator(source='auto', target='en').translate(reply.text)
        await event.edit(f"🌍 **Translation:**\n\n`{translation}`")
    except: await event.edit("❌ Error translating.")

@client.on(events.NewMessage(outgoing=True))
async def auto_translate(event):
    if "//" in event.text and not event.pattern_match:
        try:
            text, lang = event.text.split("//")
            lang = lang.strip()
            if len(lang) in [2, 5]:
                tr = GoogleTranslator(source='auto', target=lang).translate(text)
                await event.edit(tr)
        except: pass

# B. PREMIUM EMOJI
@client.on(events.NewMessage(outgoing=True, pattern=r"^\.(haha|love|sad|fire|wow|cry|lol)"))
async def premium_emoji(event):
    name = event.pattern_match.group(1)
    await event.delete()
    search_map = {"haha": "laugh", "fire": "hot", "sad": "cry"}
    query = search_map.get(name, name)
    try:
        async for msg in client.iter_messages("AnimatedStickers", search=query, limit=1):
            if msg.media:
                await client.send_file(event.chat_id, msg.media)
                return
    except: pass

# C. SPEED LINK
@client.on(events.NewMessage(outgoing=True, pattern=r"^\.link"))
async def speed_link(event):
    reply = await event.get_reply_message()
    if not reply or not reply.media:
        await event.edit("❌ Reply to media!")
        return
    try:
        file_id = str(reply.id)
        download_cache[file_id] = reply
        await event.edit(f"⚡ **Link:** `{app_url}/download/{file_id}`")
    except: await event.edit("❌ Error generating link.")

# ---------------------------------------------------------
# 3. GHOST MODE & VAULT BREAKER (THE FIX)
# ---------------------------------------------------------

@client.on(events.NewMessage(incoming=True))
async def incoming_handler(event):
    # Safe TTL Check
    ttl = getattr(event.message, 'ttl_period', None) or getattr(event.message, 'ttl_seconds', None)

    # 1. Vault Breaker
    if ttl:
        try:
            sender = await event.get_sender()
            file = await event.download_media()
            if file:
                await client.send_message("me", f"💣 **Captured View-Once**\n👤: {sender.first_name}", file=file)
                os.remove(file)
        except: pass
        return

    # 2. Ghost Mode (Forwarding with Memory)
    if event.is_private and not event.is_group and not event.is_channel:
        try:
            me = await client.get_me()
            if event.sender_id != me.id:
                # ወደ Saved Messages እንልካለን
                forwarded_msg = await client.forward_messages("me", event.message)
                
                # ዋናው ቁልፍ (The Fix): 
                # የተላከውን መልእክት ID እና የሰውዬውን ID መዝግበን እንይዛለን
                # Privacy ቢዘጋም እኛ ጋር ተመዝግቧል
                reply_cache[forwarded_msg.id] = event.sender_id
                
                # Cache እንዳይሞላ ከ1000 በላይ ከሆነ እናጽዳ (Optional)
                if len(reply_cache) > 1000:
                    reply_cache.clear()
        except Exception as e:
            logger.error(f"Ghost Forward Error: {e}")

# 3. Ghost Reply Handler
@client.on(events.NewMessage(chats="me"))
async def saved_msg_actions(event):
    # Restricted Channel Saver
    if event.text and "t.me/c/" in event.text and not event.is_reply:
        try:
            await event.edit("🔓 **Bypassing...**")
            parts = event.text.split("/")
            chan_id, msg_id = int("-100" + parts[-2]), int(parts[-1])
            msg = await client.get_messages(chan_id, ids=msg_id)
            if msg and msg.media:
                f = await client.download_media(msg)
                await client.send_file("me", f, caption="✅ **Saved!**")
                os.remove(f)
                await event.delete()
        except: await event.edit("❌ Failed.")

    # THE REAL GHOST REPLY
    if event.is_reply:
        reply_msg = await event.get_reply_message()
        target_id = None
        
        # ዘዴ 1: ከ Cache ላይ መፈለግ (Privacy ለዘጋ ሰው)
        if reply_msg.id in reply_cache:
            target_id = reply_cache[reply_msg.id]
        
        # ዘዴ 2: ካልተገኘ፣ የተለመደውን Forward Header መሞከር
        elif reply_msg.fwd_from:
             # ID ካለው (Privacy ካልዘጋ)
             if reply_msg.fwd_from.from_id:
                 target_id = getattr(reply_msg.fwd_from.from_id, 'user_id', None) or reply_msg.fwd_from.from_id

        # መልሱ ከተገኘ እንላክ
        if target_id and isinstance(target_id, int):
            try:
                await client.send_message(target_id, event.message.text)
                await event.edit(f"👻 **Sent:** {event.message.text}")
            except Exception as e:
                await event.edit(f"❌ Send Error: {e}")

# ---------------------------------------------------------
# 4. SERVER
# ---------------------------------------------------------

async def home(r): return web.Response(text="Super Userbot Running!")

async def download(r):
    fid = r.match_info['file_id']
    if fid in download_cache:
        try:
            path = await client.download_media(download_cache[fid])
            if path:
                with open(path, 'rb') as f: d = f.read()
                os.remove(path)
                return web.Response(body=d, headers={'Content-Disposition': f'attachment; filename="{os.path.basename(path)}"'})
        except: pass
    return web.Response(text="Error", status=404)

async def main():
    await client.start()
    
    app = web.Application()
    app.router.add_get('/', home)
    app.router.add_get('/download/{file_id}', download)
    
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    
    while True:
        try:
            await client(functions.account.UpdateStatusRequest(offline=False))
            await asyncio.sleep(60)
        except: await asyncio.sleep(10)

if __name__ == '__main__':
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try: loop.run_until_complete(main())
    except: pass