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
    logger.error("❌ Error: API_ID, API_HASH or SESSION variable is missing!")
    exit(1)

try:
    client = TelegramClient(StringSession(session_string), int(api_id), api_hash)
except Exception as e:
    logger.error(f"❌ Initialization Error: {e}")
    exit(1)

download_cache = {}

# ---------------------------------------------------------
# 2. PREMIUM FEATURES (Emojis, Translate, Link)
# ---------------------------------------------------------

# A. MAGIC TRANSLATOR
@client.on(events.NewMessage(outgoing=True, pattern=r"^\.tr"))
async def translate_reply(event):
    reply = await event.get_reply_message()
    if not reply or not reply.text:
        await event.edit("❌ Reply to a text message!")
        return
    try:
        await event.edit("🔄 **Translating...**")
        translation = GoogleTranslator(source='auto', target='en').translate(reply.text)
        await event.edit(f"🌍 **Translation:**\n\n`{translation}`")
    except Exception as e:
        await event.edit(f"❌ Error: {e}")

@client.on(events.NewMessage(outgoing=True))
async def auto_translate(event):
    text = event.text
    if "//" in text and not event.pattern_match:
        try:
            split_text = text.split("//")
            original_text = split_text[0]
            lang_code = split_text[1].strip()
            if len(lang_code) == 2 or len(lang_code) == 5:
                translated = GoogleTranslator(source='auto', target=lang_code).translate(original_text)
                await event.edit(translated)
        except: pass

# B. FAKE ANIMATED EMOJI (FIXED)
# አሁን የሚፈልገው 'AnimatedStickers' ከሚባለው ኦፊሴላዊ ቻናል ነው
@client.on(events.NewMessage(outgoing=True, pattern=r"^\.(haha|love|sad|fire|wow|cry|lol)"))
async def premium_emoji_hack(event):
    name = event.pattern_match.group(1)
    await event.delete() # ቴክስቱን ያጥፋው
    try:
        # ለፍለጋ የሚመች ቃል እንምረጥ
        search_query = name
        if name == "haha": search_query = "laugh"
        if name == "fire": search_query = "hot"
        
        # ከኦፊሴላዊ ቻናል ላይ ስቲከር መፈለግ
        async for message in client.iter_messages("AnimatedStickers", search=search_query, limit=1):
            if message.media:
                await client.send_file(event.chat_id, message.media)
                return
    except Exception as e:
        # ካልተገኘ በ Saved Messages ይናገር (እንዲያውቁት)
        await client.send_message("me", f"❌ Emoji Error: {e}")

# C. SPEED FREAK (Direct Link)
@client.on(events.NewMessage(outgoing=True, pattern=r"^\.link"))
async def direct_link_gen(event):
    reply = await event.get_reply_message()
    if not reply or not reply.media:
        await event.edit("❌ Reply to a media file!")
        return
    
    await event.edit("🚀 **Generating High-Speed Link...**")
    try:
        file_id = str(reply.id)
        download_cache[file_id] = reply
        final_link = f"{app_url}/download/{file_id}"
        await event.edit(f"⚡ **Direct Link Generated:**\n\n`{final_link}`\n\n_Copy to IDM/ADM for max speed!_")
    except Exception as e:
        await event.edit(f"❌ Error: {e}")

# ---------------------------------------------------------
# 3. GHOST MODE & VAULT BREAKER (FIXED & PRIORITIZED)
# ---------------------------------------------------------

@client.on(events.NewMessage(incoming=True))
async def incoming_handler(event):
    # Safe Check for TTL (Crash እንዳያደርግ)
    ttl = getattr(event.message, 'ttl_period', None) or getattr(event.message, 'ttl_seconds', None)

    # 1. Vault Breaker (View Once Saver)
    if ttl:
        try:
            sender = await event.get_sender()
            file = await event.download_media()
            await client.send_message("me", f"💣 **Captured Self-Destruct Media**\n👤 From: {sender.first_name}", file=file)
            os.remove(file)
        except Exception as e:
            logger.error(f"Vault Error: {e}")
        return

    # 2. Ghost Mode (Forwarding)
    # ማስተካከያ: የግል ቻት ከሆነ እና ከሰው ከሆነ (Channel ካልሆነ)
    if event.is_private and not event.is_channel and not event.is_group:
        try:
            # ቻት ID የራስህ ካልሆነ (አንተ ከሌላ ዲቫይስ ስትልክ እንዳይደግመው)
            me = await client.get_me()
            if event.sender_id != me.id:
                await client.forward_messages("me", event.message)
        except Exception as e:
            logger.error(f"Ghost Mode Error: {e}")

# 3. Restricted Channel Saver & Ghost Reply
@client.on(events.NewMessage(chats="me"))
async def saved_messages_handler(event):
    msg_text = event.message.text
    
    # Restricted Channel Bypass
    if msg_text and "t.me/c/" in msg_text and not event.is_reply:
        try:
            await event.edit("🔓 **Bypassing Restriction...**")
            parts = msg_text.split("/")
            channel_id = int("-100" + parts[-2])
            msg_id = int(parts[-1])
            
            message = await client.get_messages(channel_id, ids=msg_id)
            if message and message.media:
                file = await client.download_media(message)
                await client.send_file("me", file, caption="✅ **Restricted Content Saved!**")
                os.remove(file)
                await event.delete()
            else:
                await event.edit("❌ Content not found.")
        except Exception as e:
            await event.edit(f"❌ Failed: {e}")

    # Ghost Reply Logic
    if event.is_reply:
        reply_msg = await event.get_reply_message()
        if reply_msg and reply_msg.fwd_from:
            # Forward የተደረገው ከ User ከሆነ
            if reply_msg.fwd_from.from_id:
                 try:
                    # User ID ማግኘት (አንዳንድ ጊዜ user_id አንዳንድ ጊዜ just ID ሊሆን ይችላል)
                    target_id = getattr(reply_msg.fwd_from.from_id, 'user_id', None)
                    if not target_id:
                         # ቀጥታ ID ከሆነ
                         target_id = reply_msg.fwd_from.from_id
                    
                    if isinstance(target_id, int):
                        await client.send_message(target_id, event.message.text)
                        await event.edit(f"👻 **Ghost Reply:** {event.message.text}")
                 except Exception as e:
                    # ስህተት ካለ ዝም ይበል (Saved Messages እንዳይጨናነቅ)
                    pass

# ---------------------------------------------------------
# 4. SYSTEM START & SERVER
# ---------------------------------------------------------

async def handle_home(request):
    return web.Response(text="🤖 Super Userbot is Running!")

async def handle_download(request):
    file_id = request.match_info['file_id']
    if file_id in download_cache:
        message = download_cache[file_id]
        try:
            path = await client.download_media(message)
            filename = os.path.basename(path)
            with open(path, 'rb') as f:
                content = f.read()
            os.remove(path)
            return web.Response(
                body=content,
                headers={
                    'Content-Disposition': f'attachment; filename="{filename}"',
                    'Content-Type': 'application/octet-stream'
                }
            )
        except Exception as e:
            return web.Response(text=f"Stream Error: {e}", status=500)
    return web.Response(text="Link Expired", status=404)

async def main():
    logger.info("⏳ Starting Services...")
    await client.start()
    me = await client.get_me()
    logger.info(f"✅ LOGGED IN AS: {me.first_name} (ID: {me.id})")

    app = web.Application()
    app.router.add_get('/', handle_home)
    app.router.add_get('/download/{file_id}', handle_download)
    
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    logger.info(f"🚀 Web Server running on port {port}")

    while True:
        try:
            await client(functions.account.UpdateStatusRequest(offline=False))
            await asyncio.sleep(60)
        except:
            await asyncio.sleep(10)

if __name__ == '__main__':
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        pass