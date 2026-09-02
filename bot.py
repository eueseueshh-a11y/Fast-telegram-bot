import os
import re
import time
import math
from gtts import gTTS
from telethon import TelegramClient, events

# ==================== CONFIGURATION ====================
API_ID = 37277300  
API_HASH = "4667e05a4b74cdf7bfb76dacd7699f02"  
BOT_TOKEN = "8814101887:AAEJ1ZsSYNNj9B7-gKipgOwxTDeg1189HGw"  # <-- Yahan BotFather ka naya token daalein
# =======================================================

user_app = TelegramClient("user_session", API_ID, API_HASH)
bot_app = TelegramClient("bot_session", API_ID, API_HASH)

def human_readable_size(size_bytes):
    if size_bytes == 0:
        return "0 B"
    size_name = ("B", "KB", "MB", "GB", "TB")
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return f"{s} {size_name[i]}"

def human_readable_time(seconds):
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    if h > 0:
        return f"{h}h {m}m {s}s"
    elif m > 0:
        return f"{m}m {s}s"
    return f"{s}s"

async def progress_callback(current, total, status_msg, action_name, start_time, last_edit_time):
    now = time.time()
    if now - last_edit_time[0] < 3 and current != total:
        return
    last_edit_time[0] = now

    percentage = current * 100 / total
    speed = current / (now - start_time) if (now - start_time) > 0 else 0
    eta = (total - current) / speed if speed > 0 else 0
    elapsed = now - start_time

    filled_length = int(percentage // 10)
    bar = "★" * filled_length + "☆" * (10 - filled_length)

    text = (
        f"📩 **{action_name}...**\n\n"
        f"┌ [{bar}] **{percentage:.1f}%**\n"
        f"├ 🚀 **Speed** : {human_readable_size(speed)}/s\n"
        f"├ ✅ **Done** : {human_readable_size(current)}\n"
        f"├ 📦 **Total** : {human_readable_size(total)}\n"
        f"├ ⏳ **ETA** : {human_readable_time(eta)}\n"
        f"└ ⏱️ **Elapsed** : {human_readable_time(elapsed)}\n"
    )

    try:
        await status_msg.edit(text)
    except Exception:
        pass

def parse_telegram_link(link):
    p_private_topic = r"t\.me/c/(\d+)/(\d+)/(\d+)"
    p_private = r"t\.me/c/(\d+)/(\d+)"
    p_public_topic = r"t\.me/([\w_]+)/(\d+)/(\d+)"
    p_public = r"t\.me/([\w_]+)/(\d+)"
    
    match_priv_top = re.search(p_private_topic, link)
    if match_priv_top:
        return int(f"-100{match_priv_top.group(1)}"), int(match_priv_top.group(3))

    match_priv = re.search(p_private, link)
    if match_priv:
        return int(f"-100{match_priv.group(1)}"), int(match_priv.group(2))

    match_pub_top = re.search(p_public_topic, link)
    if match_pub_top:
        return match_pub_top.group(1), int(match_pub_top.group(3))

    match_pub = re.search(p_public, link)
    if match_pub:
        return match_pub.group(1), int(match_pub.group(2))

    return None, None

@bot_app.on(events.NewMessage(pattern=r"^/start"))
async def start_handler(event):
    welcome_text = "Welcome to Save Restricted Contents Bot"
    await event.respond(f"👋 **{welcome_text}**\n\nMujhe kisi bhi restricted Telegram post ka link bhejein.")
    
    voice_filename = f"welcome_{event.chat_id}.mp3"
    try:
        tts = gTTS(text=welcome_text, lang='en', slow=False)
        tts.save(voice_filename)
        await event.client.send_file(event.chat_id, voice_filename, voice_note=True)
    except Exception as e:
        print(f"[gTTS Error]: {e}")
    finally:
        if os.path.exists(voice_filename):
            os.remove(voice_filename)

@bot_app.on(events.NewMessage)
async def process_telegram_link(event):
    if event.text.startswith("/start"):
        return
    
    link = event.text.strip()
    if "t.me/" not in link:
        return

    chat_id, msg_id = parse_telegram_link(link)
    if not chat_id or not msg_id:
        await event.respond("❌ Invalid link format.")
        return

    status_msg = await event.respond("⏳ Processing started...")

    try:
        await status_msg.edit("📥 Message fetch ho raha hai...")
        target_msg = await user_app.get_messages(chat_id, ids=msg_id)

        if not target_msg:
            await status_msg.edit("❌ Message nahi mila. Check karein ki main account channel mein joined hai ya nahi.")
            return

        if not target_msg.media:
            if target_msg.text:
                await event.respond(f"📝 **Extracted Content:**\n\n{target_msg.text}")
                await status_msg.delete()
            else:
                await status_msg.edit("❌ Is message mein koi media content nahi mila.")
            return

        start_time = time.time()
        last_edit_time = [0]
        
        file_path = await user_app.download_media(
            target_msg,
            progress_callback=lambda current, total: progress_callback(
                current, total, status_msg, "Downloading", start_time, last_edit_time
            )
        )

        if not file_path or not os.path.exists(file_path):
            await status_msg.edit("❌ Download fail ho gaya.")
            return

        start_time_up = time.time()
        last_edit_time_up = [0]

        await event.client.send_file(
            event.chat_id,
            file_path,
            caption=target_msg.text or "",
            progress_callback=lambda current, total: progress_callback(
                current, total, status_msg, "Uploading", start_time_up, last_edit_time_up
            )
        )

        if os.path.exists(file_path):
            os.remove(file_path)

        await status_msg.delete()

    except Exception as e:
        await status_msg.edit(f"❌ **Error:** {str(e)}")

async def main():
    print("Starting Userbot...")
    await user_app.start()
    print("Starting Bot...")
    await bot_app.start(bot_token=BOT_TOKEN)
    print("✅ Bot successfully active ho chuka hai!")

if __name__ == "__main__":
    user_app.loop.run_until_complete(main())
    user_app.run_until_disconnected()
