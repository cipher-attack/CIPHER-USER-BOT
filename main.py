import os
import asyncio
import logging
import io  # ለ Voice Note ያስፈልጋል
from telethon import TelegramClient, events, functions, types
from telethon.sessions import StringSession
from aiohttp import web
from deep_translator import GoogleTranslator
from gtts import gTTS  # ለ Voice
import google.generativeai as genai  # ለ AI

# ---------------------------------------------------------
# 1. SETUP & CONFIGURATION
# ---------------------------------------------------------

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

api_id = os.environ.get("API_ID")
api_hash = os.environ.get("API_HASH")
session_string = os.environ.get("SESSION")
app_url = os.environ.get("RENDER_EXTERNAL_URL", "http://0.0.0.0:8080")
gemini_key = os.environ.get("GEMINI_KEY") # አዲሱ የ AI ቁልፍ

if not api_id or not api_hash or not session_string:
    logger.error("❌ Error: Credentials missing!")
    exit(1)

try:
    client = TelegramClient(StringSession(session_string), int(api_id), api_hash)
    
    # AI ማዋቀር (Gemini Setup)
    if gemini_key:
        genai.configure(api_key=gemini_key)
        model = genai.GenerativeModel('gemini-2.5-flash')
        logger.info("✅ Gemini AI Connected!")
    else:
        logger.warning("⚠️ GEMINI_KEY missing. AI features will not work.")
        
except Exception as e:
    logger.error(f"❌ Init Error: {e}")
    exit(1)

# Cache & Global Variables
reply_cache = {}
download_cache = {}
MY_ID = None  
# አንተን የሚጠሩበት ስሞች (Eavesdropper Keywords) - እዚህ ጋር ስምህን ጨምር
MY_KEYWORDS = ["cipher attack", "Cipher", "hacking", "የፈጠነ", "ብሩክ"] 

# ---------------------------------------------------------
# 2. GOD MODE FEATURES (AI & Voice) - አዲስ የተጨመሩ
# ---------------------------------------------------------

# A. THE AI CLONE (.ai [question])
@client.on(events.NewMessage(outgoing=True, pattern=r"^\.ai (.*)"))
async def ask_ai(event):
    if not gemini_key:
        await event.edit("❌ Gemini Key is missing in Render settings!")
        return
    query = event.pattern_match.group(1)
    await event.edit("🧠 **Thinking...**")
    try:
        response = model.generate_content(query)
        text = response.text
        # መልሱ በጣም ከረዘመ
        if len(text) > 4000: text = text[:4000] + "..."
        await event.edit(f"🤖 **AI Answer:**\n\n{text}")
    except Exception as e:
        await event.edit(f"❌ AI Error: {e}")

# B. THE VENTRILOQUIST (.say [text])
@client.on(events.NewMessage(outgoing=True, pattern=r"^\.say (.*)"))
async def text_to_speech(event):
    text = event.pattern_match.group(1)
    await event.delete() # ጽሁፉን እናጥፋው
    try:
        # ድምጽ ማመንጨት
        tts = gTTS(text=text, lang='en') 
        voice_file = io.BytesIO()
        tts.write_to_fp(voice_file)
        voice_file.seek(0)
        voice_file.name = "voice.ogg" # እንደ Voice Note
        
        await client.send_file(event.chat_id, voice_file, voice_note=True)
    except Exception as e:
        await client.send_message("me", f"❌ TTS Error: {e}")

# ---------------------------------------------------------
# 3. PREMIUM FEATURES (Existing)
# ---------------------------------------------------------

# C. TRANSLATOR
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

# D. PREMIUM EMOJI
@client.on(events.NewMessage(outgoing=True, pattern=r"^\.(haha|love|sad|fire|wow|cry|lol)"))
async def premium_emoji(event):
    name = event.pattern_match.group(1)
    await event.delete()
    search_map = {"haha": "laugh", "fire": "hot", "sad": "cry", "lol": "laugh"}
    query = search_map.get(name, name)
    try:
        async for msg in client.iter_messages("AnimatedStickers", search=query, limit=1):
            if msg.media:
                await client.send_file(event.chat_id, msg.media)
                return
    except: pass

# E. SPEED LINK
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
# 4. GHOST MODE, VAULT BREAKER & MONITOR (COMBINED)
# ---------------------------------------------------------

@client.on(events.NewMessage(incoming=True))
async def incoming_handler(event):
    global MY_ID
    
    # 1. THE EAVESDROPPER (አዲስ - የስም ጠለፋ)
    # ግሩፕ ውስጥ ከሆነ እና ስምህ ከተጠራ ወደ Saved Messages ይልካል
    if (event.is_group or event.is_channel) and event.raw_text:
        try:
            for keyword in MY_KEYWORDS:
                if keyword.lower() in event.raw_text.lower():
                    chat_title = event.chat.title if event.chat else "Group"
                    # የግሩፑን ሊንክ ማዘጋጀት
                    link = f"https://t.me/c/{str(event.chat_id).replace('-100', '')}/{event.id}"
                    alert_text = f"🚨 **MENTION ALERT!**\n📍 **{chat_title}**\n💬: {event.raw_text}\n🔗 [Go to Message]({link})"
                    await client.send_message("me", alert_text, link_preview=False)
                    break
        except: pass

    # Safe TTL Check (ለ View Once)
    ttl = getattr(event.message, 'ttl_period', None) or getattr(event.message, 'ttl_seconds', None)

    # 2. Vault Breaker (Self-Destruct Saver)
    if ttl:
        try:
            sender = await event.get_sender()
            file = await event.download_media()
            if file:
                await client.send_message("me", f"💣 **Captured View-Once**\n👤: {sender.first_name}", file=file)
                os.remove(file)
        except Exception as e:
            logger.error(f"Vault Error: {e}")
        return

    # 3. Ghost Mode (Saved Messages Forwarder)
    if event.is_private and not event.is_group and not event.is_channel:
        try:
            if MY_ID and event.sender_id != MY_ID:
                forwarded_msg = await client.forward_messages("me", event.message)
                if forwarded_msg:
                    reply_cache[forwarded_msg.id] = event.sender_id
                if len(reply_cache) > 500:
                    reply_cache.clear()
        except Exception as e:
            logger.error(f"Ghost Forward Error: {e}")

# 5. Ghost Reply Handler
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
                if f:
                    await client.send_file("me", f, caption="✅ **Saved!**")
                    os.remove(f)
                    await event.delete()
        except: await event.edit("❌ Failed.")

    # THE REAL GHOST REPLY
    if event.is_reply:
        reply_msg = await event.get_reply_message()
        target_id = None
        
        if reply_msg.id in reply_cache:
            target_id = reply_cache[reply_msg.id]
        elif reply_msg.fwd_from:
             if reply_msg.fwd_from.from_id:
                 target_id = getattr(reply_msg.fwd_from.from_id, 'user_id', None) or reply_msg.fwd_from.from_id

        if target_id and isinstance(target_id, int):
            try:
                await client.send_message(target_id, event.message.text)
                await event.edit(f"👻 **Sent:** {event.message.text}")
            except Exception as e:
                pass

# ---------------------------------------------------------
# 6. SERVER & STARTUP
# ---------------------------------------------------------

async def home(r): return web.Response(text="God Mode Active!")

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
    global MY_ID
    logger.info("⏳ Starting...")
    await client.start()
    
    me = await client.get_me()
    MY_ID = me.id
    logger.info(f"✅ LOGGED IN AS: {me.first_name} (ID: {MY_ID})")

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