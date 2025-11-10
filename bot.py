import os
import asyncio
import tempfile
import shutil
from concurrent.futures import ThreadPoolExecutor
from pyrogram import Client, filters
import yt_dlp
from flask import Flask

# --- Web server for Render free plan ---
app_web = Flask(__name__)

@app_web.route("/")
def home():
    return "Bot is running!"

# ---------------- Telegram Bot ----------------

BOT_TOKEN = os.getenv("BOT_TOKEN")
API_ID_ENV = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")

API_ID = int(API_ID_ENV) if API_ID_ENV else None

client_kwargs = {"bot_token": BOT_TOKEN}
if API_ID and API_HASH:
    client_kwargs["api_id"] = API_ID
    client_kwargs["api_hash"] = API_HASH

app = Client("ytbot", **client_kwargs)

executor = ThreadPoolExecutor(max_workers=2)

def _sync_download(url: str, only_audio: bool, out_dir: str):
    opts = {
        "format": "bestaudio" if only_audio else "best",
        "outtmpl": os.path.join(out_dir, "%(title)s.%(ext)s"),
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
    }
    if only_audio:
        opts["postprocessors"] = [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "192",
        }]

    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=True)
        fn = ydl.prepare_filename(info)
        if only_audio:
            fn = fn.rsplit(".", 1)[0] + ".mp3"
        return fn

async def download_media(url, only_audio):
    tmp = tempfile.mkdtemp()
    loop = asyncio.get_event_loop()
    try:
        filepath = await loop.run_in_executor(executor, _sync_download, url, only_audio, tmp)
        return filepath, tmp
    except:
        shutil.rmtree(tmp)
        raise

@app.on_message(filters.private & filters.command("start"))
async def start(_, m):
    await m.reply_text("✅ سلام! لینک یوتیوب بفرست. برای فقط صدا بنویس: صدا")

@app.on_message(filters.private & filters.text)
async def dl(_, m):
    txt = m.text.strip().lower()
    if not txt.startswith("http"):
        return await m.reply("لینک معتبر نیست.")

    only_audio = ("صدا" in txt) or ("audio" in txt)
    msg = await m.reply("⏳ درحال دانلود...")

    try:
        file, tmp = await download_media(txt, only_audio)
        if only_audio:
            await m.reply_audio(file)
        else:
            await m.reply_video(file)
        await msg.delete()
        shutil.rmtree(tmp)
    except Exception as e:
        await msg.edit(f"❌ خطا: {e}")

if __name__ == "__main__":
    import threading
    threading.Thread(target=lambda: app_web.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))).start()
    app.run()
