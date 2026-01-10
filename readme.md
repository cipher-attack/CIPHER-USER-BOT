# Userbot ያዝ እንግዲህ lela ሰው እንዳታሳይ su

**Project:** Personal Telethon Automation Script
**Status:** Active
**Author:** [cipher_attack]

---

### 1. Configuration (Environment Variables)

Before deploying, ensure these variables are set in the .env file or cloud dashboard.

* `API_ID` & `API_HASH`: Obtained from my.telegram.org.
* `SESSION`: The Telethon string session.
* `GEMINI_KEY`: (Optional) Google Gemini API key for AI features.
* `RENDER_EXTERNAL_URL`: For keeping the web server alive on PaaS.

---

### 2. Sniper Protocol (Giveaways & Quizzes)

The core logic for winning giveaways. Follow the **Target -> Lock -> Fire** sequence strictly.

**Step 1: Set Target Channel**
* Command: `.monitor`
* Usage: Send inside the channel hosting the giveaway. Captures Chat ID.

**Step 2: Hunter Lock (Safety Mechanism)**
* Command: `.hunt` (Must Reply)
* Usage: **Reply** to a message sent by the giveaway host (admin or bot).
* *Why:* This ensures the bot *only* triggers when that specific User ID posts. Prevents misfiring on random comments.

**Step 3: Arm the Sniper**
* **Mode A (Flash):** For "First comment wins" speed tasks.
  * Command: `.win [text]`
  * Example: `.win 100birr` (Auto-replies "100birr" instantly when the Hunter Target posts).
* **Mode B (Quiz):** For AI-based questions.
  * Command: `.quiz`
  * Action: Uses Gemini AI to solve the question and reply immediately.

**Stop Command:**
* `.stop` - Disables all sniper modes and clears targets.

---

### 3. General Commands Reference

#### AI & Intelligence
* `.ai [query]` - Ask Gemini AI. (Reply to an image to analyze it).
* `.img [prompt]` - Generate an image using Pollinations AI.
* `.tr` - Reply to any message to translate it to English.

#### Media & Utilities
* `.song [name]` - Downloads music from YouTube/SoundCloud.
* `.vpic` - Reply to a video. Trims it to 9 seconds and sets it as a Telegram Video Profile.
* `.web [url]` - Takes a screenshot of a website and sends it as an image.
* `.qrl [link]` - Converts text/link into a QR Code.

#### Identity & Trolling
* `.clone` - Reply to a user to copy their Name, Bio, and Profile Picture.
* `.revert` - Restores original profile (Must have cloned someone first).
* `.say [text]` - Generates a voice note (supports Amharic detection).
* `.hack` - Displays a fake "hacking" terminal animation.

#### Administration
* `.purge` - Reply to a message. Deletes that message and everything below it.
* `.scrape [channel]` - Scrapes active members from a target group and invites them to the current group.
* `.all [message]` - Tags all members in the group (Hidden mentions).

---

### 4. Background Processes (Ghost Mode)

**Private Forwarding:**
* Incoming private messages (PMs) are automatically forwarded to "Saved Messages" if unseen.
* Reply mechanism: Replying to the forwarded message in "Saved Messages" sends the reply to the actual user anonymously.

**View-Once Bypass:**
* Automatically detects "View Once" (destructible) media and saves a copy to "Saved Messages".

**AFK System:**
* `.afk [reason]` - Sets status to Away. Auto-replies to DMs.
* Typing anything in any chat disables AFK automatically.

---

### 5. Known Issues / Notes

* **Sniper Latency:** The `.quiz` mode depends on Gemini API speed. usually < 1.5s.
* **Safety:** `.scrape` has a limit of 40 users per run to prevent account bans.
* **Hosting:** The web server (aiohttp) is included to satisfy port binding requirements on platforms like Render.
