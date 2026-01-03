import os
import asyncio
import logging
import io
from telethon import TelegramClient, events, functions, types
from telethon.sessions import StringSession
from aiohttp import web
from deep_translator import GoogleTranslator
from gtts import gTTS
import google.generativeai as genai

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
    # Gemini Setup
    if gemini_key:
        genai.configure(api_key=gemini_key)
        model = genai.GenerativeModel('gemini-2-flash')
        logger.info("✅ Gemini AI Connected!")
except Exception as e:
    logger.error(f"❌ Init Error: {e}")
    exit(1)

reply_cache = {}
download_cache = {}
MY_ID = None
# አንተን የሚጠሩበት ስሞች (Eavesdropper Keywords)
MY_KEYWORDS = ["መላኩ", "Melaku", "Bro", "አድሚን"] # እዚህ ጋር ስምህን ቀይር

# ---------------------------------------------------------
# 2. GOD MODE FEATURES (AI, Voice, Monitor)
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
        # መልሱ በጣም ረጅም ከሆነ እንዳይቆርጠው
        text = response.text
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
        # ድምጽ ማመንጨት (Google TTS)
        tts = gTTS(text=text, lang='en') # lang='am' ካልከው አማርኛ ይሞክራል
        voice_file = io.BytesIO()
        tts.write_to_fp(voice_file)
        voice_file.seek(0)
        voice_file.name = "voice.ogg" # እንደ Voice Note እንዲላክ
        
        await client.send_file(event.chat_id, voice_file, voice_note=True)
    except Exception as e:
        await client.send_message("me", f"❌ TTS Error: {e}")

# ---------------------------------------------------------
# 3. EXISTING UTILITIES (Translator, Emoji, Link)
# ---------------------------------------------------------

@client.on(events.NewMessage(outgoing=True, pattern=r"^\.tr"))
async def translate_reply(event):
    reply = await event.get_reply_message()
    if not reply or not reply.text: return
    try:
        await event.edit("🔄")
        tr = GoogleTranslator(source='auto', target='en').translate(reply.text)
        await event.edit(f"🌍 `{tr}`")
    except: pass

@client.on(events.NewMessage(outgoing=True))
async def auto_translate(event):
    if "//" in event.text and not event.pattern_match:
        try:
            text, lang = event.text.split("//")
            tr = GoogleTranslator(source='auto', target=lang.strip()).translate(text)
            await event.edit(tr)
        except: pass

@client.on(events.NewMessage(outgoing=True, pattern=r"^\.(haha|love|sad|fire|wow|cry|lol)"))
async def premium_emoji(event):
    name = event.pattern_match.group(1)
    await event.delete()
    search_map = {"haha": "laugh", "fire": "hot", "sad": "cry", "lol": "laugh"}
    try:
        async for msg in client.iter_messages("AnimatedStickers", search=search_map.get(name, name), limit=1):
            if msg.media: await client.send_file(event.chat_id, msg.media)
    except: pass

@client.on(events.NewMessage(outgoing=True, pattern=r"^\.link"))
async def speed_link(event):
    reply = await event.get_reply_message()
    if reply and reply.media:
        file_id = str(reply.id)
        download_cache[file_id] = reply
        await event.edit(f"⚡ `{app_url}/download/{file_id}`")

# ---------------------------------------------------------
# 4. MONITORING & GHOST SYSTEM
# ---------------------------------------------------------

@client.on(events.NewMessage(incoming=True))
async def incoming_handler(event):
    global MY_ID
    
    # 1. THE EAVESDROPPER (የስም ጠለፋ)
    # ግሩፕ ውስጥ ከሆነ እና ስምህ ከተጠራ
    if event.is_group or event.is_channel:
        if event.raw_text:
            for keyword in MY_KEYWORDS:
                if keyword.lower() in event.raw_text.lower():
                    # ስምህ የተጠራበትን ግሩፕ እና መልእክት ወደ አንተ ይልካል
                    chat_title = event.chat.title if event.chat else "Group"
                    link = f"https://t.me/c/{event.chat_id}/{event.id}".replace("-100", "")
                    alert_text = f"🚨 **MENTION ALERT!**\n📍 **{chat_title}**\n💬: {event.raw_text}\n🔗 [Go to Message]({link})"
                    await client.send_message("me", alert_text, link_preview=False)
                    break
    
    # 2. VAULT BREAKER
    ttl = getattr(event.message, 'ttl_period', None) or getattr(event.message, 'ttl_seconds', None)
    if ttl:
        try:
            f = await event.download_media()
            if f:
                sender = await event.get_sender()
                await client.send_message("me", f"💣 **View-Once** from {sender.first_name}", file=f)
                os.remove(f)
        except: pass
        return

    # 3. GHOST MODE
    if event.is_private and not event.is_group and MY_ID and event.sender_id != MY_ID:
        try:
            fwd = await client.forward_messages("me", event.message)
            if fwd: reply_cache[fwd.id] = event.sender_id
            if len(reply_cache) > 500: reply_cache.clear()
        except: pass

@client.on(events.NewMessage(chats="me"))
async def saved_actions(event):
    # Restricted Saver
    if event.text and "t.me/c/" in event.text and not event.is_reply:
        try:
            await event.edit("🔓")
            parts = event.text.split("/")
            msg = await client.get_messages(int("-100" + parts[-2]), ids=int(parts[-1]))
            if msg and msg.media:
                f = await client.download_media(msg)
                if f:
                    await client.send_file("me", f, caption="✅")
                    os.remove(f)
                    await event.delete()
        except: await event.edit("❌")

    # Ghost Reply
    if event.is_reply:
        reply = await event.get_reply_message()
        tid = reply_cache.get(reply.id)
        if not tid and reply.fwd_from:
            tid = getattr(reply.fwd_from.from_id, 'user_id', None) or reply.fwd_from.from_id
        if tid and isinstance(tid, int):
            try:
                await client.send_message(tid, event.message.text)
                await event.edit(f"👻 {event.message.text}")
            except: pass

# ---------------------------------------------------------
# 5. SERVER
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
    await client.start()
    me = await client.get_me()
    MY_ID = me.id
    logger.info(f"✅ GOD MODE STARTED FOR: {me.first_name}")

    app = web.Application()
    app.router.add_get('/', home)
    app.router.add_get('/download/{file_id}', download)
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