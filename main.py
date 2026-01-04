import os
import asyncio
import logging
import io
import random
from telethon import TelegramClient, events, functions, types
from telethon.sessions import StringSession
from aiohttp import web
from deep_translator import GoogleTranslator
from gtts import gTTS
import google.generativeai as genai
from PIL import Image  # ለ AI Vision (ፎቶ እንዲያይ)

# ---------------------------------------------------------
# 1. SETUP & CONFIGURATION
# ---------------------------------------------------------

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

api_id = os.environ.get("API_ID")
api_hash = os.environ.get("API_HASH")
session_string = os.environ.get("SESSION")
app_url = os.environ.get("RENDER_EXTERNAL_URL", "http://0.0.0.0:8080")
gemini_key = os.environ.get("GEMINI_KEY")

if not api_id or not api_hash or not session_string:
    logger.error("❌ Error: Credentials missing!")
    exit(1)

try:
    client = TelegramClient(StringSession(session_string), int(api_id), api_hash)

    # AI Setup (Vision Model)
    if gemini_key:
        genai.configure(api_key=gemini_key)
        # 1.5-flash ፎቶ ማየት ይችላል እና ፈጣን ነው
        model = genai.GenerativeModel('gemini-2.5-flash')
        logger.info("✅ Gemini Vision AI Connected!")
    else:
        logger.warning("⚠️ GEMINI_KEY missing. AI features will not work.")

except Exception as e:
    logger.error(f"❌ Init Error: {e}")
    exit(1)

# Cache & Global Variables
reply_cache = {}
download_cache = {}
MY_ID = None  
MY_KEYWORDS = ["cipher", "CIPHER", "first comment", "biruk", "ብሩክ"] # ስምህን እዚህ አሻሽል

# ---------------------------------------------------------
# 2. SINGULARITY FEATURES (Vision, Art, Profiler, Voice)
# ---------------------------------------------------------

# A. THE ALL-SEEING EYE (ፎቶ የሚያየው AI)
# አጠቃቀም: .ai [ጥያቄ] (ወይም ፎቶ Reply አድርገህ .ai ይሄ ምንድን ነው?)
@client.on(events.NewMessage(outgoing=True, pattern=r"^\.ai ?(.*)"))
async def ai_handler(event):
    if not gemini_key:
        await event.edit("❌ Gemini Key Missing!")
        return

    query = event.pattern_match.group(1)
    reply = await event.get_reply_message()
    
    await event.edit("🧠 **Thinking...**")
    
    try:
        # 1. ፎቶ ካለው (Vision Mode)
        if reply and reply.media and reply.photo:
            await event.edit("👁️ **Analyzing Image...**")
            # ፎቶውን ወደ memory ማውረድ
            photo_data = await reply.download_media(file=bytes)
            img = Image.open(io.BytesIO(photo_data))
            
            # ለ AI መላክ (ፎቶ + ጥያቄ)
            prompt = query if query else "Describe this image in detail."
            response = model.generate_content([prompt, img])
        
        # 2. ጽሁፍ ብቻ ከሆነ (Text Mode)
        else:
            if not query:
                await event.edit("❌ Write something or reply to a photo!")
                return
            response = model.generate_content(query)

        # ውጤት
        text = response.text
        if len(text) > 4000: text = text[:4000] + "..."
        await event.edit(f"🤖 **AI:**\n\n{text}")

    except Exception as e:
        await event.edit(f"❌ AI Error: {e}")

# B. THE ARTIST (.img [prompt])
@client.on(events.NewMessage(outgoing=True, pattern=r"^\.img (.*)"))
async def generate_image(event):
    prompt = event.pattern_match.group(1)
    await event.edit(f"🎨 **Painting:** `{prompt}`...")
    
    try:
        # Pollinations AI (Free Art Generation)
        encoded_prompt = prompt.replace(" ", "%20")
        style = random.choice(["cinematic", "cyberpunk", "anime", "photorealistic"])
        url = f"https://image.pollinations.ai/prompt/{encoded_prompt}%20{style}"
        
        await client.send_file(event.chat_id, url, caption=f"🎨 **Art:** {prompt}")
        await event.delete()
    except Exception as e:
        await event.edit(f"❌ Art Error: {e}")

# C. THE PROFILER (.info)
@client.on(events.NewMessage(outgoing=True, pattern=r"^\.info"))
async def user_info(event):
    reply = await event.get_reply_message()
    if not reply:
        await event.edit("❌ Reply to a user!")
        return
    
    await event.edit("🕵️ **Scanning User...**")
    try:
        user = await reply.get_sender()
        info_text = f"👤 **USER DOSSIER**\n"
        info_text += f"🆔 **ID:** `{user.id}`\n"
        info_text += f"🗣️ **Name:** {user.first_name} {user.last_name if user.last_name else ''}\n"
        info_text += f"🔗 **Username:** @{user.username if user.username else 'None'}\n"
        info_text += f"🤖 **Bot:** {'Yes' if user.bot else 'No'}\n"
        info_text += f"💎 **Premium:** {'Yes' if user.premium else 'No'}\n"
        
        # የፕሮፋይል ፎቶ ማውረድ
        photo = await client.download_profile_photo(user.id)
        
        if photo:
            await client.send_file(event.chat_id, photo, caption=info_text)
            os.remove(photo)
            await event.delete()
        else:
            await event.edit(info_text)

    except Exception as e:
        await event.edit(f"❌ Scan Error: {e}")

# D. THE VENTRILOQUIST (.say [text])
@client.on(events.NewMessage(outgoing=True, pattern=r"^\.say (.*)"))
async def text_to_speech(event):
    text = event.pattern_match.group(1)
    await event.delete()
    try:
        tts = gTTS(text=text, lang='en') 
        voice_file = io.BytesIO()
        tts.write_to_fp(voice_file)
        voice_file.seek(0)
        voice_file.name = "voice.ogg"
        await client.send_file(event.chat_id, voice_file, voice_note=True)
    except Exception as e:
        await client.send_message("me", f"❌ TTS Error: {e}")

# ---------------------------------------------------------
# 3. UTILITIES (Translator, Emoji, Link)
# ---------------------------------------------------------

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
    
    # 1. THE EAVESDROPPER (Eavesdropper)
    if (event.is_group or event.is_channel) and event.raw_text:
        try:
            for keyword in MY_KEYWORDS:
                if keyword.lower() in event.raw_text.lower():
                    chat_title = event.chat.title if event.chat else "Group"
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