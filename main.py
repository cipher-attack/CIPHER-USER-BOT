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
from PIL import Image

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

    # AI Setup
    if gemini_key:
        genai.configure(api_key=gemini_key)
        # ለፍጥነት እና ለእይታ ምርጡ ሞዴል gemini-1.5-flash ነው
        model = genai.GenerativeModel('gemini-1.5-flash')
        logger.info("✅ Gemini AI Connected!")
    else:
        logger.warning("⚠️ GEMINI_KEY missing. AI features will not work.")

except Exception as e:
    logger.error(f"❌ Init Error: {e}")
    exit(1)

# --- GLOBAL VARIABLES ---
reply_cache = {}
download_cache = {}
MY_ID = None  
MY_KEYWORDS = ["cipher", "CIPHER", "first comment", "biruk", "ብሩክ"] 

# --- SNIPER VARIABLES (ለ Giveaway) ---
TARGET_CHANNEL_ID = None
SNIPER_TEXT = None
SNIPER_MODE = "OFF" # "FLASH" (ለፍጥነት) or "QUIZ" (ለጥያቄ)

# ---------------------------------------------------------
# 2. GIVEAWAY SNIPER COMMANDS (አዲሱ ጨዋታ)
# ---------------------------------------------------------

@client.on(events.NewMessage(outgoing=True, pattern=r"^\.monitor"))
async def set_monitor(event):
    """አሁን ያለህበትን ቻናል ኢላማ ያደርጋል"""
    global TARGET_CHANNEL_ID
    TARGET_CHANNEL_ID = event.chat_id
    title = event.chat.title if event.chat else str(event.chat_id)
    await event.delete() # ሚስጥራዊነት
    await client.send_message("me", f"🎯 **Sniper Locked on:** `{title}`\n🆔 `{TARGET_CHANNEL_ID}`")

@client.on(events.NewMessage(outgoing=True, pattern=r"^\.win (.*)"))
async def set_flash_mode(event):
    """Flash Mode: ጽሁፍ አዘጋጅቶ መጠበቅ (Me, Done, etc)"""
    global SNIPER_MODE, SNIPER_TEXT
    SNIPER_TEXT = event.pattern_match.group(1)
    SNIPER_MODE = "FLASH"
    await event.delete() # ሚስጥራዊነት
    await client.send_message("me", f"⚡ **Flash Mode ARMED!**\nAuto-Reply: `{SNIPER_TEXT}`")

@client.on(events.NewMessage(outgoing=True, pattern=r"^\.quiz"))
async def set_quiz_mode(event):
    """Quiz Mode: AI በሰውኛ እና በአጭሩ እንዲመልስ"""
    global SNIPER_MODE
    SNIPER_MODE = "QUIZ"
    await event.delete() # ሚስጥራዊነት
    await client.send_message("me", f"🧠 **Quiz Mode ARMED!**\nAI will answer instantly & human-like.")

@client.on(events.NewMessage(outgoing=True, pattern=r"^\.stop"))
async def stop_sniper(event):
    """Sniping ማቆሚያ"""
    global SNIPER_MODE, TARGET_CHANNEL_ID
    SNIPER_MODE = "OFF"
    TARGET_CHANNEL_ID = None
    await event.delete() # ሚስጥራዊነት
    await client.send_message("me", "🛑 **Sniper Disengaged.**")

# ---------------------------------------------------------
# 3. GOD MODE COMMANDS (AI, Art, Info, Voice)
# ---------------------------------------------------------

@client.on(events.NewMessage(outgoing=True, pattern=r"^\.ai ?(.*)"))
async def ai_handler(event):
    if not gemini_key: return await event.edit("❌ No Key")
    query = event.pattern_match.group(1)
    reply = await event.get_reply_message()
    await event.edit("🧠")
    try:
        # Vision Mode (ፎቶ ከሆነ)
        if reply and reply.media and reply.photo:
            photo_data = await reply.download_media(file=bytes)
            img = Image.open(io.BytesIO(photo_data))
            prompt = query if query else "Describe this image detail."
            response = model.generate_content([prompt, img])
        # Text Mode
        else:
            if not query: return await event.edit("❌ Text/Image needed")
            response = model.generate_content(query)
        
        text = response.text
        if len(text) > 4000: text = text[:4000] + "..."
        await event.edit(f"🤖 **AI:**\n\n{text}")
    except Exception as e: await event.edit(f"❌ Error: {e}")

@client.on(events.NewMessage(outgoing=True, pattern=r"^\.img (.*)"))
async def generate_image(event):
    prompt = event.pattern_match.group(1)
    await event.edit(f"🎨 `{prompt}`...")
    try:
        encoded = prompt.replace(" ", "%20")
        style = random.choice(["cinematic", "anime", "photorealistic"])
        url = f"https://image.pollinations.ai/prompt/{encoded}%20{style}"
        await client.send_file(event.chat_id, url, caption=f"🎨 {prompt}")
        await event.delete()
    except: await event.edit("❌ Error")

@client.on(events.NewMessage(outgoing=True, pattern=r"^\.info"))
async def user_info(event):
    reply = await event.get_reply_message()
    if not reply: return await event.edit("❌ Reply to user")
    await event.edit("🕵️")
    try:
        user = await reply.get_sender()
        info = f"👤 **DOSSIER**\n🆔 `{user.id}`\n🗣️ {user.first_name}\n🔗 @{user.username}\n🤖 Bot: {user.bot}\n💎 Premium: {user.premium}"
        photo = await client.download_profile_photo(user.id)
        if photo:
            await client.send_file(event.chat_id, photo, caption=info)
            os.remove(photo)
            await event.delete()
        else: await event.edit(info)
    except: await event.edit("❌ Error")

@client.on(events.NewMessage(outgoing=True, pattern=r"^\.say (.*)"))
async def text_to_speech(event):
    text = event.pattern_match.group(1)
    await event.delete()
    try:
        tts = gTTS(text=text, lang='en')
        f = io.BytesIO()
        tts.write_to_fp(f)
        f.seek(0)
        f.name = "voice.ogg"
        await client.send_file(event.chat_id, f, voice_note=True)
    except: pass

# ---------------------------------------------------------
# 4. UTILITIES (Premium Tools)
# ---------------------------------------------------------

@client.on(events.NewMessage(outgoing=True, pattern=r"^\.tr"))
async def translate_reply(event):
    reply = await event.get_reply_message()
    if reply and reply.text:
        try:
            await event.edit("🔄")
            tr = GoogleTranslator(source='auto', target='en').translate(reply.text)
            await event.edit(f"🌍 `{tr}`")
        except: pass

@client.on(events.NewMessage(outgoing=True))
async def auto_translate(event):
    if "//" in event.text and not event.pattern_match:
        try:
            t, l = event.text.split("//")
            tr = GoogleTranslator(source='auto', target=l.strip()).translate(t)
            await event.edit(tr)
        except: pass

@client.on(events.NewMessage(outgoing=True, pattern=r"^\.(haha|love|sad|fire|wow|cry|lol)"))
async def premium_emoji(event):
    name = event.pattern_match.group(1)
    await event.delete()
    m = {"haha":"laugh","fire":"hot","sad":"cry","lol":"laugh"}
    try:
        async for x in client.iter_messages("AnimatedStickers", search=m.get(name,name), limit=1):
            if x.media:
                await client.send_file(event.chat_id, x.media)
                return
    except: pass

@client.on(events.NewMessage(outgoing=True, pattern=r"^\.link"))
async def speed_link(event):
    r = await event.get_reply_message()
    if r and r.media:
        download_cache[str(r.id)] = r
        await event.edit(f"⚡ `{app_url}/download/{r.id}`")

# ---------------------------------------------------------
# 5. CORE HANDLER (INCOMING MESSAGES - THE BRAIN)
# ---------------------------------------------------------

@client.on(events.NewMessage(incoming=True))
async def incoming_handler(event):
    global MY_ID, SNIPER_MODE

    # --- A. SNIPER LOGIC (Giveaway Winner) ---
    # ይህ ከሁሉም በላይ ቅድሚያ አለው (Priority 1)
    if TARGET_CHANNEL_ID and event.chat_id == TARGET_CHANNEL_ID:
        
        # 1. Flash Mode (Me/Done)
        if SNIPER_MODE == "FLASH" and SNIPER_TEXT:
            try:
                # ፖስቱ ገና እንደወጣ ይልካል
                await client.send_message(event.chat_id, SNIPER_TEXT, reply_to=event.id)
                SNIPER_MODE = "OFF"
                await client.send_message("me", f"✅ **FLASH SNIPED:** {SNIPER_TEXT}")
            except: pass
            return

        # 2. Quiz Mode (AI Smart Answer)
        elif SNIPER_MODE == "QUIZ" and event.text:
            try:
                # Prompt Engineering: AI እንደ ሰው እንዲያስብ እና አጭር መልስ እንዲሰጥ
                prompt = f"""
                Task: Answer this quiz question instantly.
                Rules:
                1. Give ONLY the direct answer. No explanations.
                2. If it's a number, just write the number.
                3. Keep it extremely short (1-3 words max).
                4. Do NOT use markdown or bold text.
                5. Act like a human typing fast.
                Question: {event.text}
                """
                response = model.generate_content(prompt)
                answer = response.text.strip()
                
                await client.send_message(event.chat_id, answer, reply_to=event.id)
                SNIPER_MODE = "OFF"
                await client.send_message("me", f"✅ **QUIZ SNIPED:** {answer}")
            except: pass
            return

    # --- B. EAVESDROPPER (Keyword Monitor) ---
    if (event.is_group or event.is_channel) and event.raw_text:
        try:
            for k in MY_KEYWORDS:
                if k.lower() in event.raw_text.lower():
                    l = f"https://t.me/c/{str(event.chat_id).replace('-100','')}/{event.id}"
                    await client.send_message("me", f"🚨 **{k}** Found!\n🔗 {l}")
                    break
        except: pass

    # --- C. VAULT BREAKER (View Once) ---
    ttl = getattr(event.message, 'ttl_period', None) or getattr(event.message, 'ttl_seconds', None)
    if ttl:
        try:
            sender = await event.get_sender()
            f = await event.download_media()
            if f:
                await client.send_message("me", f"💣 **View-Once** from {sender.first_name}", file=f)
                os.remove(f)
        except: pass
        return

    # --- D. GHOST MODE (Forwarder) ---
    if event.is_private and not event.is_group and not event.is_channel:
        try:
            if MY_ID and event.sender_id != MY_ID:
                # ቦቱ የላከውን መልእክት ወደ Saved Messages
                fwd = await client.forward_messages("me", event.message)
                # መታወቂያውን Cache ማድረግ (ለ Reply)
                if fwd: reply_cache[fwd.id] = event.sender_id
                if len(reply_cache) > 500: reply_cache.clear()
        except: pass

# ---------------------------------------------------------
# 6. SAVED MESSAGES HANDLER (Ghost Reply & Bypass)
# ---------------------------------------------------------

@client.on(events.NewMessage(chats="me"))
async def saved_msg_actions(event):
    # Restricted Channel Saver
    if event.text and "t.me/c/" in event.text and not event.is_reply:
        try:
            await event.edit("🔓")
            parts = event.text.split("/")
            chan_id = int("-100" + parts[-2])
            msg_id = int(parts[-1])
            msg = await client.get_messages(chan_id, ids=msg_id)
            if msg and msg.media:
                f = await client.download_media(msg)
                if f:
                    await client.send_file("me", f, caption="✅")
                    os.remove(f)
                    await event.delete()
        except: await event.edit("❌")

    # Ghost Reply
    if event.is_reply:
        reply_msg = await event.get_reply_message()
        target_id = None
        
        # ከ Cache ይፈልጋል
        if reply_msg.id in reply_cache:
            target_id = reply_cache[reply_msg.id]
        # ከ Forward Header ይፈልጋል
        elif reply_msg.fwd_from:
             if reply_msg.fwd_from.from_id:
                 target_id = getattr(reply_msg.fwd_from.from_id, 'user_id', None) or reply_msg.fwd_from.from_id

        if target_id and isinstance(target_id, int):
            try:
                await client.send_message(target_id, event.message.text)
                await event.edit(f"👻 **Sent:** {event.message.text}")
            except: pass

# ---------------------------------------------------------
# 7. SERVER & STARTUP
# ---------------------------------------------------------

async def home(r): return web.Response(text="Bot Active!")

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