import os
import asyncio
import logging
import io
import random
import yt_dlp
import edge_tts
from telethon import TelegramClient, events, functions, types
from telethon.sessions import StringSession
from telethon.tl.functions.messages import GetStickerSetRequest
from telethon.tl.types import InputStickerSetShortName
from telethon.tl.functions.channels import InviteToChannelRequest
from aiohttp import web
from deep_translator import GoogleTranslator
from gtts import gTTS
from pydub import AudioSegment
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

# Connection Retries added to keep connection alive
client = TelegramClient(StringSession(session_string), int(api_id), api_hash, connection_retries=None)

try:
    if gemini_key:
        genai.configure(api_key=gemini_key)
        model = genai.GenerativeModel('gemini-2.5-flash')
        logger.info("✅ Gemini AI Connected!")
    else:
        logger.warning("⚠️ GEMINI_KEY missing.")
except Exception as e:
    logger.error(f"❌ Init Error: {e}")

# --- GLOBAL VARIABLES ---
reply_cache = {}
download_cache = {}
MY_ID = None  
MY_KEYWORDS = ["cipher", "CIPHER", "first comment", "biruk", "ብሩክ"] 
ORIGINAL_PROFILE = {}
IS_AFK = False
AFK_REASON = ""

# --- SNIPER VARIABLES ---
TARGET_CHANNEL_ID = None
SNIPER_TEXT = None
SNIPER_MODE = "OFF"
HUNTER_TARGET_ID = None 

# ---------------------------------------------------------
# 2. GIVEAWAY SNIPER COMMANDS
# ---------------------------------------------------------

@client.on(events.NewMessage(outgoing=True, pattern=r"^\.monitor"))
async def set_monitor(event):
    global TARGET_CHANNEL_ID
    TARGET_CHANNEL_ID = event.chat_id
    title = event.chat.title if event.chat else str(event.chat_id)
    await event.delete()
    await client.send_message("me", f"🎯 **Sniper Locked on:** `{title}`\n🆔 `{TARGET_CHANNEL_ID}`")

@client.on(events.NewMessage(outgoing=True, pattern=r"^\.hunt"))
async def set_hunt_target(event):
    global HUNTER_TARGET_ID
    reply = await event.get_reply_message()
    if not reply:
        return await event.edit("❌ **Error:** Reply to a message to hunt that user!")
    HUNTER_TARGET_ID = reply.sender_id
    await event.delete()
    await client.send_message("me", f"🦅 **Hunter Active!**\n🆔 Locked ID: `{HUNTER_TARGET_ID}`")

@client.on(events.NewMessage(outgoing=True, pattern=r"^\.win (.*)"))
async def set_flash_mode(event):
    global SNIPER_MODE, SNIPER_TEXT
    SNIPER_TEXT = event.pattern_match.group(1)
    SNIPER_MODE = "FLASH"
    await event.delete()
    status = f"⚡ **Flash Mode ARMED!**\nAuto-Reply: `{SNIPER_TEXT}`"
    if HUNTER_TARGET_ID: status += "\n🔒 **Target Locked:** YES"
    else: status += "\n⚠️ **Target Locked:** NO"
    await client.send_message("me", status)

@client.on(events.NewMessage(outgoing=True, pattern=r"^\.quiz"))
async def set_quiz_mode(event):
    global SNIPER_MODE
    SNIPER_MODE = "QUIZ"
    await event.delete()
    await client.send_message("me", f"🧠 **Quiz Mode ARMED!**")

@client.on(events.NewMessage(outgoing=True, pattern=r"^\.stop"))
async def stop_sniper(event):
    global SNIPER_MODE, TARGET_CHANNEL_ID, HUNTER_TARGET_ID
    SNIPER_MODE = "OFF"
    TARGET_CHANNEL_ID = None
    HUNTER_TARGET_ID = None 
    await event.delete()
    await client.send_message("me", "🛑 **Sniper & Hunter Disengaged.**")

# ---------------------------------------------------------
# 3. GOD MODE COMMANDS
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
        await event.edit(f"🤖 **AI:**\n\n{response.text}")
    except Exception as e: await event.edit(f"❌ Error: {e}")

@client.on(events.NewMessage(outgoing=True, pattern=r"^\.img (.*)"))
async def generate_image(event):
    prompt = event.pattern_match.group(1)
    await event.edit(f"🎨 `{prompt}`...")
    try:
        encoded = prompt.replace(" ", "%20")
        url = f"https://image.pollinations.ai/prompt/{encoded}%20cinematic"
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
        info = f"👤 **DOSSIER**\n🆔 `{user.id}`\n🗣️ {user.first_name}"
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
    await event.edit("🗣️")
    try:
        is_amharic = any("\u1200" <= char <= "\u137F" for char in text)
        voice = 'am-ET-AmehaNeural' if is_amharic else 'en-US-ChristopherNeural'
        communicate = edge_tts.Communicate(text, voice)
        filename = "voice.mp3"
        await communicate.save(filename)
        await client.send_file(event.chat_id, filename, voice_note=True)
        if os.path.exists(filename): os.remove(filename)
        await event.delete()
    except: await event.edit("❌ Voice Error")

@client.on(events.NewMessage(outgoing=True, pattern=r"^\.clone"))
async def clone_identity(event):
    global ORIGINAL_PROFILE
    reply = await event.get_reply_message()
    if not reply: return await event.edit("❌ Reply first")
    await event.edit("🎭")
    try:
        user = await reply.get_sender()
        me = await client.get_me()
        me_full = await client(functions.users.GetFullUserRequest(me))
        if not ORIGINAL_PROFILE:
            my_photo = await client.download_profile_photo("me", file=bytes)
            ORIGINAL_PROFILE = {"first_name": me.first_name, "last_name": me.last_name, "about": me_full.full_user.about, "photo_bytes": my_photo}
        target_full = await client(functions.users.GetFullUserRequest(user))
        target_photo = await client.download_profile_photo(user, file=bytes)
        await client(functions.account.UpdateProfileRequest(first_name=user.first_name, last_name=user.last_name or "", about=target_full.full_user.about or ""))
        if target_photo:
            f = io.BytesIO(target_photo)
            f.name = "clone.jpg"
            up = await client.upload_file(f)
            await client(functions.photos.UploadProfilePhotoRequest(file=up))
        await event.edit(f"🎭 **Identity Stolen!**")
    except: await event.edit(f"❌ Error")

@client.on(events.NewMessage(outgoing=True, pattern=r"^\.revert"))
async def revert_identity(event):
    global ORIGINAL_PROFILE
    if not ORIGINAL_PROFILE: return await event.edit("❌ No backup")
    await event.edit("🔄")
    try:
        await client(functions.account.UpdateProfileRequest(first_name=ORIGINAL_PROFILE["first_name"], last_name=ORIGINAL_PROFILE["last_name"] or "", about=ORIGINAL_PROFILE["about"] or ""))
        if ORIGINAL_PROFILE.get("photo_bytes"):
            f = io.BytesIO(ORIGINAL_PROFILE["photo_bytes"])
            f.name = "revert.jpg"
            up = await client.upload_file(f)
            await client(functions.photos.UploadProfilePhotoRequest(file=up))
        ORIGINAL_PROFILE = {}
        await event.edit("✅")
    except: await event.edit(f"❌ Error")

@client.on(events.NewMessage(outgoing=True, pattern=r"^\.scrape (.*)"))
async def scrape_members(event):
    target = event.pattern_match.group(1)
    my_group = event.chat_id
    await event.delete()
    try:
        entity = await client.get_entity(target)
        participants = await client.get_participants(entity, aggressive=True)
        count = 0
        for user in participants:
            if not user.bot and (isinstance(user.status, types.UserStatusOnline) or isinstance(user.status, types.UserStatusRecently)):
                if count >= 40: break
                try:
                    await client(InviteToChannelRequest(my_group, [user]))
                    count += 1
                    await asyncio.sleep(2) # Faster scrape
                except: pass
        await client.send_message("me", f"✅ **Scraped {count} users**")
    except: pass

# ---------------------------------------------------------
# 4. UTILITIES (Premium Tools)
# ---------------------------------------------------------

@client.on(events.NewMessage(outgoing=True, pattern=r"^\.song (.*)"))
async def download_song(event):
    song_name = event.pattern_match.group(1)
    await event.edit(f"🔍 `{song_name}`...")
    try:
        ydl_opts = {'format': 'bestaudio/best', 'outtmpl': 'song.%(ext)s', 'quiet': True, 'noplaylist': True, 'nocheckcertificate': True}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            try: info = ydl.extract_info(f"ytsearch:{song_name}", download=False)
            except: info = ydl.extract_info(f"scsearch:{song_name}", download=False)
            if 'entries' in info and len(info['entries']) > 0:
                ydl.download([info['entries'][0]['webpage_url']])
                await event.edit("⬆️")
                for ext in ['webm', 'm4a', 'mp3']:
                    if os.path.exists(f"song.{ext}"):
                        await client.send_file(event.chat_id, f'song.{ext}', caption=f"🎧 {song_name}")
                        os.remove(f"song.{ext}")
                        break
                await event.delete()
    except: await event.edit("❌ Error")

@client.on(events.NewMessage(outgoing=True, pattern=r"^\.vpic"))
async def set_video_profile(event):
    reply = await event.get_reply_message()
    if not reply or not reply.media: return await event.edit("❌ Reply video")
    await event.edit("🔄")
    try:
        vid = await client.download_media(reply, file="v.mp4")
        out = "v_safe.mp4"
        os.system(f'ffmpeg -i "{vid}" -t 9 -vf scale="512:512:force_original_aspect_ratio=decrease,pad=512:512:(ow-iw)/2:(oh-ih)/2" -c:v libx264 -an "{out}" -y')
        if os.path.exists(out):
            await client(functions.photos.UploadProfilePhotoRequest(video=await client.upload_file(out), video_start_ts=0.0))
            await event.edit("✅")
            os.remove(out)
        os.remove(vid)
    except: await event.edit("❌")

@client.on(events.NewMessage(outgoing=True, pattern=r"^\.purge"))
async def purge_messages(event):
    reply = await event.get_reply_message()
    if not reply: return
    await event.delete()
    try:
        msgs = []
        async for msg in client.iter_messages(event.chat_id, min_id=reply.id - 1): msgs.append(msg)
        await client.delete_messages(event.chat_id, msgs)
    except: pass

@client.on(events.NewMessage(outgoing=True, pattern=r"^\.all (.*)"))
async def tag_all(event):
    text = event.pattern_match.group(1)
    await event.delete()
    try:
        mentions = []
        async for user in client.iter_participants(event.chat_id):
            if not user.bot: mentions.append(f"<a href='tg://user?id={user.id}'>\u200b</a>")
        for i in range(0, len(mentions), 100):
            await client.send_message(event.chat_id, f"📢 {text}\n{''.join(mentions[i:i+100])}", parse_mode='html')
    except: pass

@client.on(events.NewMessage(outgoing=True, pattern=r"^\.hack"))
async def hacker_animation(event):
    for step in ["💻 Connect...", "🔓 Access...", "📂 Stealing...", "✅ **DONE**"]:
        await event.edit(f"`{step}`")
        await asyncio.sleep(1)

@client.on(events.NewMessage(outgoing=True, pattern=r"^\.afk ?(.*)"))
async def set_afk(event):
    global IS_AFK, AFK_REASON
    IS_AFK = True
    AFK_REASON = event.pattern_match.group(1) or "Busy"
    await event.edit(f"💤 **AFK:** `{AFK_REASON}`")

@client.on(events.NewMessage(outgoing=True, pattern=r"^\.tr"))
async def translate_reply(event):
    reply = await event.get_reply_message()
    if reply:
        tr = GoogleTranslator(source='auto', target='en').translate(reply.text)
        await event.edit(f"🌍 `{tr}`")

@client.on(events.NewMessage(outgoing=True))
async def auto_translate(event):
    if "//" in event.text:
        try:
            t, l = event.text.split("//")
            tr = GoogleTranslator(source='auto', target=l.strip()).translate(t)
            await event.edit(tr)
        except: pass

@client.on(events.NewMessage(outgoing=True, pattern=r"^\.(haha|love|sad|fire|wow|cry|lol)"))
async def premium_emoji(event):
    name = event.pattern_match.group(1)
    await event.delete()
    packs = ["HotCherry", "Duck", "UtyaDuck", "Pepe"]
    target = {"haha":"😂","lol":"🤣","love":"❤️","sad":"😢","cry":"😭","fire":"🔥","wow":"😮"}.get(name)
    try:
        found = False
        for pack in packs:
            if found: break
            stickers = await client(GetStickerSetRequest(stickerset=InputStickerSetShortName(short_name=pack), hash=0))
            for doc in stickers.documents:
                for attr in doc.attributes:
                    if isinstance(attr, types.DocumentAttributeSticker) and target in attr.alt:
                        await client.send_file(event.chat_id, doc)
                        found = True
                        break
    except: pass

@client.on(events.NewMessage(outgoing=True))
async def unset_afk_check(event):
    global IS_AFK
    if IS_AFK and not event.text.startswith(".afk"):
        IS_AFK = False
        await client.send_message(event.chat_id, "✅ **Online**")

# ---------------------------------------------------------
# 5. CORE HANDLER
# ---------------------------------------------------------

@client.on(events.NewMessage(incoming=True))
async def incoming_handler(event):
    global MY_ID, SNIPER_MODE, IS_AFK, AFK_REASON, HUNTER_TARGET_ID

    if IS_AFK and event.is_private:
        sender = await event.get_sender()
        if sender and not sender.bot:
            await event.reply(f"🤖 **AFK:** `{AFK_REASON}`")

    # --- SNIPER LOGIC ---
    if TARGET_CHANNEL_ID and event.chat_id == TARGET_CHANNEL_ID:
        # HUNT CHECK
        if HUNTER_TARGET_ID and event.sender_id != HUNTER_TARGET_ID:
            return 

        if SNIPER_MODE == "FLASH" and SNIPER_TEXT:
            try:
                await client.send_message(event.chat_id, SNIPER_TEXT, reply_to=event.id)
                SNIPER_MODE = "OFF"
                await client.send_message("me", f"✅ **SNIPED:** {SNIPER_TEXT}")
            except: pass
            return
            
        elif SNIPER_MODE == "QUIZ" and event.text:
            try:
                prompt = f"Ans: {event.text}. Short."
                response = model.generate_content(prompt)
                answer = response.text.strip()
                await client.send_message(event.chat_id, answer, reply_to=event.id)
                SNIPER_MODE = "OFF"
                await client.send_message("me", f"✅ **QUIZ:** {answer}")
            except: pass
            return

    # EAVESDROPPER
    if (event.is_group or event.is_channel) and event.raw_text:
        try:
            for k in MY_KEYWORDS:
                if k.lower() in event.raw_text.lower():
                    await client.send_message("me", f"🚨 **{k}** Found!\n🔗 https://t.me/c/{str(event.chat_id).replace('-100','')}/{event.id}")
                    break
        except: pass

    # VAULT BREAKER
    if event.message.ttl_period or (event.media and hasattr(event.media, 'ttl_seconds') and event.media.ttl_seconds):
        try:
            f = await event.download_media(file=bytes)
            if f:
                img = io.BytesIO(f)
                img.name = "vault.jpg"
                await client.send_file("me", img, caption=f"💣 **Vault**")
        except: pass

    # GHOST
    if event.is_private and not event.is_group and not event.is_channel:
        try:
            if MY_ID and event.sender_id != MY_ID:
                fwd = await client.forward_messages("me", event.message)
                if fwd: reply_cache[fwd.id] = event.sender_id
                if len(reply_cache) > 200: reply_cache.clear()
        except: pass

@client.on(events.NewMessage(chats="me"))
async def saved_msg_actions(event):
    if event.is_reply:
        reply_msg = await event.get_reply_message()
        target = reply_cache.get(reply_msg.id)
        if target:
            try:
                await client.send_message(target, event.message.text)
                await event.edit(f"👻 **Sent**")
            except: pass

# ---------------------------------------------------------
# 7. SERVER
# ---------------------------------------------------------

async def home(r): return web.Response(text="Bot Active!")
async def download(r): return web.Response(text="N/A")

async def main():
    global MY_ID
    logger.info("⏳ Starting...")
    await client.start()
    me = await client.get_me()
    MY_ID = me.id
    logger.info(f"✅ LOGGED IN AS: {me.first_name}")

    app = web.Application()
    app.router.add_get('/', home)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()

    await client.run_until_disconnected() # BEST FOR STABILITY

if __name__ == '__main__':
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try: loop.run_until_complete(main())
    except: pass