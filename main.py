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
    exit(1)

try:
    client = TelegramClient(StringSession(session_string), int(api_id), api_hash)
    if gemini_key:
        genai.configure(api_key=gemini_key)
        model = genai.GenerativeModel('gemini-2.5-flash')
except Exception as e:
    exit(1)

# Variables
reply_cache = {}
download_cache = {}
MY_ID = None  
MY_KEYWORDS = ["cipher", "first comment", "biruk", "ብሩክ"] 

# --- SNIPER VARIABLES ---
TARGET_CHANNEL_ID = None # ግሩፑ
TARGET_SENDER_ID = None  # የሚለጥፈው ሰው (Admin/Channel) ID
SNIPER_TEXT = None
SNIPER_MODE = "OFF"

# ---------------------------------------------------------
# 2. SILENT SNIPER COMMANDS (ራስ በራስ የሚጠፉ)
# ---------------------------------------------------------

@client.on(events.NewMessage(outgoing=True, pattern=r"^\.monitor"))
async def set_monitor(event):
    """ግሩፑን ይመርጣል"""
    global TARGET_CHANNEL_ID
    TARGET_CHANNEL_ID = event.chat_id
    # መልእክቱን በራሱ ያጥፋዋል (Stealth)
    await event.delete()
    # ለራስህ ብቻ ምልክት (Saved Messages)
    await client.send_message("me", f"🎯 **Monitoring Chat:** `{TARGET_CHANNEL_ID}`")

@client.on(events.NewMessage(outgoing=True, pattern=r"^\.target"))
async def set_target_sender(event):
    """አድሚኑን ለመምረጥ (Reply አድርገህ .target በል)"""
    global TARGET_SENDER_ID
    reply = await event.get_reply_message()
    
    if reply:
        TARGET_SENDER_ID = reply.sender_id
        await event.delete() # ትዕዛዙን ማጥፋት
        name = getattr(reply.sender, 'first_name', 'Channel')
        await client.send_message("me", f"🔒 **Target Locked on User/Channel:** `{name}` (ID: {TARGET_SENDER_ID})")
    else:
        await event.edit("❌ Reply to the admin/channel post!")
        await asyncio.sleep(2)
        await event.delete()

@client.on(events.NewMessage(outgoing=True, pattern=r"^\.win (.*)"))
async def set_flash_mode(event):
    """Flash Mode"""
    global SNIPER_MODE, SNIPER_TEXT
    SNIPER_TEXT = event.pattern_match.group(1)
    SNIPER_MODE = "FLASH"
    await event.delete() # ትዕዛዙን ማጥፋት
    await client.send_message("me", f"⚡ **Flash Mode ARMED!**\nAuto-Reply: `{SNIPER_TEXT}`")

@client.on(events.NewMessage(outgoing=True, pattern=r"^\.quiz"))
async def set_quiz_mode(event):
    """Quiz Mode"""
    global SNIPER_MODE
    SNIPER_MODE = "QUIZ"
    await event.delete() # ትዕዛዙን ማጥፋት
    await client.send_message("me", f"🧠 **Quiz Mode ARMED!**")

@client.on(events.NewMessage(outgoing=True, pattern=r"^\.stop"))
async def stop_sniper(event):
    """ሁሉንም ያቆማል"""
    global SNIPER_MODE, TARGET_CHANNEL_ID, TARGET_SENDER_ID
    SNIPER_MODE = "OFF"
    TARGET_CHANNEL_ID = None
    TARGET_SENDER_ID = None
    await event.delete()
    await client.send_message("me", "🛑 **Sniper & Target Cleared.**")

# ---------------------------------------------------------
# 3. GOD MODE & UTILITIES (የተለመዱት)
# ---------------------------------------------------------

@client.on(events.NewMessage(outgoing=True, pattern=r"^\.ai ?(.*)"))
async def ai_handler(event):
    if not gemini_key: return await event.edit("❌ No Key")
    query = event.pattern_match.group(1)
    reply = await event.get_reply_message()
    await event.edit("🧠")
    try:
        if reply and reply.media and reply.photo:
            photo_data = await reply.download_media(file=bytes)
            img = Image.open(io.BytesIO(photo_data))
            prompt = query if query else "Describe this image detail."
            response = model.generate_content([prompt, img])
        else:
            if not query: return await event.edit("❌ Text needed")
            response = model.generate_content(query)
        await event.edit(f"🤖 **AI:**\n\n{response.text[:4000]}")
    except: await event.edit("❌ Error")

@client.on(events.NewMessage(outgoing=True, pattern=r"^\.img (.*)"))
async def generate_image(event):
    prompt = event.pattern_match.group(1)
    await event.edit(f"🎨 `{prompt}`...")
    try:
        url = f"https://image.pollinations.ai/prompt/{prompt.replace(' ', '%20')}"
        await client.send_file(event.chat_id, url, caption=f"🎨 {prompt}")
        await event.delete()
    except: await event.edit("❌ Error")

@client.on(events.NewMessage(outgoing=True, pattern=r"^\.info"))
async def user_info(event):
    reply = await event.get_reply_message()
    if not reply: return
    await event.edit("🕵️")
    try:
        user = await reply.get_sender()
        info = f"👤 **ID:** `{user.id}`\n🗣️ {user.first_name}"
        photo = await client.download_profile_photo(user.id)
        if photo:
            await client.send_file(event.chat_id, photo, caption=info)
            os.remove(photo)
            await event.delete()
        else: await event.edit(info)
    except: pass

@client.on(events.NewMessage(outgoing=True, pattern=r"^\.say (.*)"))
async def tts_h(event):
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

@client.on(events.NewMessage(outgoing=True, pattern=r"^\.tr"))
async def tr_h(event):
    r = await event.get_reply_message()
    if r and r.text:
        try:
            tr = GoogleTranslator(source='auto', target='en').translate(r.text)
            await event.edit(f"🌍 `{tr}`")
        except: pass

@client.on(events.NewMessage(outgoing=True))
async def auto_tr(event):
    if "//" in event.text:
        try:
            t, l = event.text.split("//")
            tr = GoogleTranslator(source='auto', target=l.strip()).translate(t)
            await event.edit(tr)
        except: pass

@client.on(events.NewMessage(outgoing=True, pattern=r"^\.(haha|love|sad|fire|wow|cry|lol)"))
async def em_h(event):
    n = event.pattern_match.group(1)
    await event.delete()
    m = {"haha":"laugh","fire":"hot","sad":"cry","lol":"laugh"}
    try:
        async for x in client.iter_messages("AnimatedStickers", search=m.get(n,n), limit=1):
            if x.media: await client.send_file(event.chat_id, x.media); return
    except: pass

@client.on(events.NewMessage(outgoing=True, pattern=r"^\.link"))
async def ln_h(event):
    r = await event.get_reply_message()
    if r and r.media:
        download_cache[str(r.id)] = r
        await event.edit(f"⚡ `{app_url}/download/{r.id}`")

# ---------------------------------------------------------
# 4. CORE HANDLER (THE BRAIN)
# ---------------------------------------------------------

@client.on(events.NewMessage(incoming=True))
async def incoming_handler(event):
    global MY_ID, SNIPER_MODE

    # --- A. PRECISION SNIPER LOGIC ---
    if TARGET_CHANNEL_ID and event.chat_id == TARGET_CHANNEL_ID:
        
        # 1. Check Sender (ዒላማው ትክክል ነው?)
        # TARGET_SENDER_ID ከተሞላ፣ የላከው ሰው እሱ መሆኑን ያረጋግጣል
        if TARGET_SENDER_ID:
            if event.sender_id != TARGET_SENDER_ID:
                return # የተሳሳተ ሰው ነው (ዝም በል)
        
        # 2. Fire Flash Mode
        if SNIPER_MODE == "FLASH" and SNIPER_TEXT:
            try:
                await client.send_message(event.chat_id, SNIPER_TEXT, reply_to=event.id)
                SNIPER_MODE = "OFF"
                await client.send_message("me", f"✅ **SNIPED:** {SNIPER_TEXT}")
            except: pass
            return

        # 3. Fire Quiz Mode
        elif SNIPER_MODE == "QUIZ" and event.text:
            try:
                # Prompt: Human-like, Short Answer
                prompt = f"Answer this quiz directly. Shortest answer possible (1-3 words). No punctuation. Q: {event.text}"
                res = model.generate_content(prompt)
                ans = res.text.strip()
                await client.send_message(event.chat_id, ans, reply_to=event.id)
                SNIPER_MODE = "OFF"
                await client.send_message("me", f"✅ **QUIZ SNIPED:** {ans}")
            except: pass
            return

    # --- B. EAVESDROPPER ---
    if (event.is_group or event.is_channel) and event.raw_text:
        for k in MY_KEYWORDS:
            if k.lower() in event.raw_text.lower():
                l = f"https://t.me/c/{str(event.chat_id).replace('-100','')}/{event.id}"
                await client.send_message("me", f"🚨 **{k}** Found!\n🔗 {l}")
                break

    # --- C. VAULT BREAKER ---
    ttl = getattr(event.message, 'ttl_period', None) or getattr(event.message, 'ttl_seconds', None)
    if ttl:
        try:
            f = await event.download_media()
            if f:
                s = await event.get_sender()
                await client.send_message("me", f"💣 **View-Once** from {s.first_name}", file=f)
                os.remove(f)
        except: pass
        return

    # --- D. GHOST MODE ---
    if event.is_private and not event.is_group and MY_ID and event.sender_id != MY_ID:
        try:
            fwd = await client.forward_messages("me", event.message)
            if fwd: reply_cache[fwd.id] = event.sender_id
            if len(reply_cache) > 500: reply_cache.clear()
        except: pass

# Saved Messages Handler
@client.on(events.NewMessage(chats="me"))
async def saved_actions(event):
    if event.text and "t.me/c/" in event.text and not event.is_reply:
        try:
            await event.edit("🔓")
            p = event.text.split("/")
            m = await client.get_messages(int("-100" + p[-2]), ids=int(p[-1]))
            if m and m.media:
                f = await client.download_media(m)
                if f:
                    await client.send_file("me", f, caption="✅")
                    os.remove(f)
                    await event.delete()
        except: await event.edit("❌")

    if event.is_reply:
        r = await event.get_reply_message()
        tid = reply_cache.get(r.id)
        if not tid and r.fwd_from:
            tid = getattr(r.fwd_from.from_id, 'user_id', None) or r.fwd_from.from_id
        if tid and isinstance(tid, int):
            try:
                await client.send_message(tid, event.message.text)
                await event.edit(f"👻 {event.message.text}")
            except: pass

# ---------------------------------------------------------
# 5. SERVER
# ---------------------------------------------------------
async def home(r): return web.Response(text="Sniper Active!")
async def dl(r):
    fid = r.match_info['file_id']
    if fid in download_cache:
        try:
            p = await client.download_media(download_cache[fid])
            if p:
                with open(p, 'rb') as f: d = f.read()
                os.remove(p)
                return web.Response(body=d, headers={'Content-Disposition': f'attachment'})
        except: pass
    return web.Response(text="404")

async def main():
    global MY_ID
    await client.start()
    me = await client.get_me()
    MY_ID = me.id
    logger.info(f"✅ SYSTEM READY: {me.first_name}")

    app = web.Application()
    app.router.add_get('/', home)
    app.router.add_get('/download/{file_id}', dl)
    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, '0.0.0.0', int(os.environ.get("PORT", 8080))).start()
    
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