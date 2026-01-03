import os
import asyncio
import logging
import mimetypes
from telethon import TelegramClient, events, functions, types
from telethon.sessions import StringSession
from aiohttp import web
from googletrans import Translator

# ---------------------------------------------------------
# 1. SETUP & CONFIGURATION (መጀመሪያ የሚነሱ)
# ---------------------------------------------------------

# Logging (ስህተት ካለ እንዲያሳየን)
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Environment Variables (ከ Render Setting የሚመጡ)
api_id = os.environ.get("API_ID")
api_hash = os.environ.get("API_HASH")
session_string = os.environ.get("SESSION")
app_url = os.environ.get("RENDER_EXTERNAL_URL", "http://0.0.0.0:8080") # ለ Direct Link

# መረጃዎች መሞላታቸውን ማረጋገጥ
if not api_id or not api_hash or not session_string:
    logger.error("❌ Error: API_ID, API_HASH or SESSION variable is missing!")
    exit(1)

# Initialize Clients
try:
    client = TelegramClient(StringSession(session_string), int(api_id), api_hash)
    translator = Translator()
except Exception as e:
    logger.error(f"❌ Initialization Error: {e}")
    exit(1)

# ለ Direct Link መያዣ (Cache)
download_cache = {}

# ---------------------------------------------------------
# 2. PREMIUM FEATURES (ለከፈሉ ብቻ የተፈቀዱትን መስበር)
# ---------------------------------------------------------

# A. MAGIC TRANSLATOR (ቋንቋ አዋቂው)
# 1. ሰው የላከውን Reply አድርገህ ".tr" ስትል ይተረጉማል
@client.on(events.NewMessage(outgoing=True, pattern=r"^\.tr"))
async def translate_reply(event):
    reply = await event.get_reply_message()
    if not reply or not reply.text:
        await event.edit("❌ Reply to a text message!")
        return
    try:
        await event.edit("🔄 **Translating...**")
        translation = translator.translate(reply.text, dest='en')
        await event.edit(f"🌍 **Translation:**\n\n`{translation.text}`")
    except Exception as e:
        await event.edit(f"❌ Error: {e}")

# 2. አንተ የጻፍከውን ወደ ፈለከው ቋንቋ መቀየር (ምሳሌ: "ሰላም //en")
@client.on(events.NewMessage(outgoing=True))
async def auto_translate(event):
    text = event.text
    if "//" in text and not event.pattern_match: # ከሌሎች command ጋር እንዳይጋጭ
        try:
            split_text = text.split("//")
            original_text = split_text[0]
            lang_code = split_text[1].strip()
            if len(lang_code) == 2:
                translated = translator.translate(original_text, dest=lang_code)
                await event.edit(translated.text)
        except: pass

# B. FAKE ANIMATED EMOJI (ኢሞጂ አስማት)
# ".haha", ".love", ".fire" ወዘተ ብለህ ስትጽፍ የሚንቀሳቀስ Sticker ይተካዋል
@client.on(events.NewMessage(outgoing=True, pattern=r"^\.(haha|love|sad|fire|wow|cry)"))
async def premium_emoji_hack(event):
    name = event.pattern_match.group(1)
    await event.delete()
    try:
        # በነፃ የሚገኝ Sticker ቻናል ላይ ይፈልግና ይልካል
        async for message in client.iter_messages("AnimatedEmojies", search=name, limit=1):
            if message.media:
                await client.send_file(event.chat_id, message.media)
    except: pass

# C. SPEED FREAK (Direct Link Generator)
# ፋይልን Reply አድርገህ ".link" ስትል ለ IDM የሚሆን ሊንክ ይሰጣል
@client.on(events.NewMessage(outgoing=True, pattern=r"^\.link"))
async def direct_link_gen(event):
    reply = await event.get_reply_message()
    if not reply or not reply.media:
        await event.edit("❌ Reply to a media file!")
        return
    
    await event.edit("🚀 **Generating High-Speed Link...**")
    try:
        file_id = str(reply.id)
        download_cache[file_id] = reply # ፋይሉን Cache ውስጥ መያዝ
        
        # የመጨረሻውን ሊንክ ማዘጋጀት
        # ማሳሰቢያ: RENDER_EXTERNAL_URL ከሌለ በ IP ይሞክራል
        final_link = f"{app_url}/download/{file_id}"
        await event.edit(f"⚡ **Direct Link Generated:**\n\n`{final_link}`\n\n_Copy to IDM/ADM for max speed!_")
    except Exception as e:
        await event.edit(f"❌ Error: {e}")

# ---------------------------------------------------------
# 3. GHOST MODE & VAULT BREAKER (ሚስጥራዊ ስራዎች)
# ---------------------------------------------------------

# A. INCOMING HANDLER (ከሰው ወደ እኔ ሲመጣ)
@client.on(events.NewMessage(incoming=True))
async def incoming_handler(event):
    # 1. THE VAULT BREAKER (View Once / Timer Media Saver)
    if event.message.ttl_seconds:
        try:
            sender = await event.get_sender()
            file = await event.download_media()
            await client.send_message("me", f"💣 **Captured Self-Destruct Media**\n👤 From: {sender.first_name}", file=file)
            os.remove(file) # ማስረጃ ማጥፋት
        except Exception as e:
            logger.error(f"Vault Error: {e}")
        return # የView Once ከያዘ በኋላ Ghost Mode አያስፈልግም

    # 2. GHOST MODE (Private Chat Forwarding)
    if event.is_private:
        try:
            # መልእክቱን ወደ Saved Messages ገልብጠው (ሳይነበብ እንዲቀር)
            await client.forward_messages("me", event.message)
        except: pass

# B. RESTRICTED CHANNEL BYPASS (ከ Saved Messages ሆነህ ሊንክ ስትልክ)
@client.on(events.NewMessage(chats="me"))
async def saved_messages_handler(event):
    msg_text = event.message.text
    
    # 1. Restricted Channel Link Detector
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

    # 2. GHOST REPLY (ከ Saved Messages ሆነህ Reply ስታደርግ)
    if event.is_reply:
        reply_msg = await event.get_reply_message()
        # Reply የተደረገው ከሰው Forward የተደረገ ከሆነ
        if reply_msg.fwd_from and hasattr(reply_msg.fwd_from.from_id, 'user_id'):
            target_id = reply_msg.fwd_from.from_id.user_id
            try:
                # እንደ እኔ ሆኖ ለሰውዬው ይላክ
                await client.send_message(target_id, event.message.text)
                await event.edit(f"👻 **Ghost Reply:** {event.message.text}")
            except Exception as e:
                await event.edit(f"❌ Error: {e}")

# ---------------------------------------------------------
# 4. WEB SERVER & ALWAYS ONLINE (የጀርባ አጥንት)
# ---------------------------------------------------------

# Home Route
async def handle_home(request):
    return web.Response(text="🤖 Super Userbot is Running!")

# File Streaming Route (ለ Direct Link)
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
    
    # Start Telegram Client
    await client.start()
    me = await client.get_me()
    logger.info(f"✅ LOGGED IN AS: {me.first_name} (ID: {me.id})")

    # Start Web Server
    app = web.Application()
    app.router.add_get('/', handle_home)
    app.router.add_get('/download/{file_id}', handle_download)
    
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    logger.info(f"🚀 Web Server running on port {port}")

    # Keep Online Loop
    logger.info("😎 Always Online Loop Started!")
    while True:
        try:
            await client(functions.account.UpdateStatusRequest(offline=False))
            # logger.info("Ping sent (Online)") # ሎግ እንዳይበዛ ይህን መደበቅ ይቻላል
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