import os
import asyncio
import tempfile
import shutil
from concurrent.futures import ThreadPoolExecutor
from pyrogram import Client, filters
import yt_dlp

# ---------- Config from env ----------
BOT_TOKEN = os.getenv("BOT_TOKEN")

# API_ID/API_HASH optional — اگر نبود، فقط با bot token کار می‌کنیم
API_ID_ENV = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")

API_ID = None
if API_ID_ENV:
    try:
        API_ID = int(API_ID_ENV)
    except Exception:
        API_ID = None

# ---------- create client (works with or without api_id/api_hash) ----------
client_kwargs = {"bot_token": BOT_TOKEN}
if API_ID and API_HASH:
    client_kwargs["api_id"] = API_ID
    client_kwargs["api_hash"] = API_HASH

app = Client("ytbot", **client_kwargs)

# ---------- helper: blocking download runs in thread ----------
executor = ThreadPoolExecutor(max_workers=2)

def _sync_download(url: str, only_audio: bool, out_dir: str):
    """Blocking function: download via yt_dlp into out_dir, return filepath."""
    opts = {
        "format": "bestaudio/best" if only_audio else "best",
        "outtmpl": os.path.join(out_dir, "%(title)s.%(ext)s"),
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        # progress_hooks could be added
    }
    if only_audio:
        opts["postprocessors"] = [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "192",
        }]

    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=True)
        filename = ydl.prepare_filename(info)
        if only_audio:
            filename = os.path.splitext(filename)[0] + ".mp3"
        return filename

async def download_media(url: str, only_audio: bool):
    tmpdir = tempfile.mkdtemp(prefix="ytbot_")
    loop = asyncio.get_event_loop()
    try:
        filepath = await loop.run_in_executor(executor, _sync_download, url, only_audio, tmpdir)
        return filepath, tmpdir
    except Exception as e:
        # cleanup on error
        try:
            shutil.rmtree(tmpdir)
        except Exception:
            pass
        raise e

# ---------- Handlers ----------
@app.on_message(filters.private & filters.command("start"))
async def on_start(client, message):
    await message.reply_text("✅ سلام! لینک یوتیوب بفرست. اگر فقط صدا می‌خوای بنویس 'صدا' یا 'audio' بعد لینک.")

@app.on_message(filters.private & filters.text & ~filters.command("start"))
async def on_message(client, message):
    text = message.text.strip()
    # بررسی وجود لینک ساده
    if not (text.startswith("http://") or text.startswith("https://")):
        await message.reply_text("لطفاً یک لینک معتبر ارسال کن (مثال: https://www.youtube.com/watch?v=...).")
        return

    # تشخیص درخواست فقط صدا: اگر کلمه 'صدا' یا 'audio' در متن باشد
    lower = text.lower()
    only_audio = ("صدا" in lower) or ("audio" in lower) or ("voice" in lower)

    # اگر کاربر لینک و کلمه را در یک خط فرستاده بود (مثلاً "link صدا")، جدا کردن لینک از بقیه
    parts = text.split()
    url = None
    for p in parts:
        if p.startswith("http://") or p.startswith("https://"):
            url = p
            break
    if not url:
        await message.reply_text("لینک پیدا نشد. لینک را به صورت کامل بفرست.")
        return

    status = await message.reply_text("⏳ در حال دانلود، صبور باش ...")
    try:
        filepath, tmpdir = await download_media(url, only_audio=only_audio)

        # محدودیت ارسال: اگر فایل خیلی بزرگ است، اطلاع بده (تلگرام محدودیت سرور دارد)
        max_size_bytes = 45 * 1024 * 1024  # حدود 45 MB به عنوان محافظه‌کار
        try:
            fsize = os.path.getsize(filepath)
        except Exception:
            fsize = None

        if fsize and fsize > max_size_bytes:
            await status.edit_text(f"فایل خروجی بزرگ است ({fsize // (1024*1024)} MB). ارسال مستقیم غیرفعال است.")
            # می‌توانیم آپلود به فضای ابری اضافه کنیم؛ فعلاً فایل را پاک می‌کنیم
            try:
                shutil.rmtree(tmpdir)
            except Exception:
                pass
            return

        await status.edit_text("📤 در حال ارسال فایل ...")
        # اگر فایل صوتی است، ارسال به صورت document یا audio
        if only_audio:
            await message.reply_audio(audio=filepath)
        else:
            await message.reply_video(video=filepath)

        await status.delete()
        # پاکسازی فایل‌ها
        try:
            shutil.rmtree(tmpdir)
        except Exception:
            pass

    except Exception as e:
        await status.edit_text(f"❌ خطا در دانلود یا ارسال:\n{e}")

# ---------- startup checks ----------
if __name__ == "__main__":
    # سریع بررسی minimal env
    missing = []
    if not BOT_TOKEN:
        missing.append("BOT_TOKEN")
    # API_ID/API_HASH optional; only warn if one present but not both
    if (API_ID_ENV and not API_HASH) or (API_HASH and not API_ID_ENV):
        missing.append("API_ID/API_HASH (incomplete)")

    if missing:
        print("Warning: missing env vars:", missing)
        print("BOT_TOKEN is required. API_ID/API_HASH are optional (only for user client).")
    else:
        print("Env OK. Starting bot...")

    app.run()
