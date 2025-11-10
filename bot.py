import os
from flask import Flask, request
from pyrogram import Client, filters
import yt_dlp

# --- تنظیمات از محیط ---
BOT_TOKEN = os.getenv("BOT_TOKEN")
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")   # مثل: https://yourapp.onrender.com/webhook

app = Flask(__name__)

bot = Client(
    "bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)


# ---- وقتی تلگرام پیام می‌فرستد ----
@app.route("/webhook", methods=["POST"])
def webhook():
    update = request.get_json()
    bot.process_update(update)
    return "OK", 200


@app.route("/", methods=["GET"])
def home():
    return "✅ Telegram Bot Active", 200


# ---- دستور دانلود ویدئو / صدا ----
@bot.on_message(filters.private & filters.text)
async def download_handler(client, message):
    url = message.text.strip()

    msg = await message.reply("⏳ در حال پردازش...")

    try:
        # تنظیم دانلود
        ydl_opts = {
            "outtmpl": "%(title)s.%(ext)s",
            "format": "best",
        }

        # اگر کاربر گفت "صدا"
        if "audio" in url or "voice" in url:
            ydl_opts["format"] = "bestaudio/best"
            ydl_opts["postprocessors"] = [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }]
            url = url.replace("audio ", "").replace("voice ", "")

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            file_name = ydl.prepare_filename(info)

        await msg.edit("✅ ارسال فایل...")

        await client.send_document(
            chat_id=message.chat.id,
            document=file_name
        )

        os.remove(file_name)

    except Exception as e:
        await msg.edit(f"❌ خطا: {e}")


# ---- اجرای Bot + Webhook ----
if __name__ == "__main__":
    import asyncio
    from threading import Thread

    # اجرای Pyrogram در Thread جداگانه
    def run_bot():
        bot.run()

    Thread(target=run_bot).start()

    # ست کردن وب‌هوک
    async def set_webhook():
        async with bot:
            await bot.set_webhook(WEBHOOK_URL)

    asyncio.get_event_loop().run_until_complete(set_webhook())

    # اجرای Flask
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
