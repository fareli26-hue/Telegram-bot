import os
from flask import Flask, request
from pyrogram import Client, filters
import yt_dlp

# ------- تنظیمات محیط ---------
BOT_TOKEN = os.getenv("BOT_TOKEN")
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

app = Flask(__name__)

bot = Client(
    "bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

@app.route("/webhook", methods=["POST"])
def webhook():
    update = request.get_json()
    bot.process_update(update)
    return "OK", 200


@app.route("/", methods=["GET"])
def home():
    return "✅ Bot Running", 200


@bot.on_message(filters.private & filters.text)
async def download_handler(client, message):
    url = message.text.strip()

    msg = await message.reply("⏳ در حال پردازش... لطفاً صبر کنید")

    # ✅ آپدیت yt-dlp برای حل مشکل Video Unavailable
    os.system("pip install -U yt-dlp")

    try:
        ydl_opts = {
            "outtmpl": "%(title)s.%(ext)s",
            "format": "best",
            "cookiesfrombrowser": ("chrome",),
        }

        # ✅ اگر فقط صدا بخواهد:
        if url.startswith("audio "):
            url = url.replace("audio ", "")
            ydl_opts["format"] = "bestaudio/best"
            ydl_opts["postprocessors"] = [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': 192,
            }]

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            file_name = ydl.prepare_filename(info)

        await msg.edit("✅ ارسال فایل ...")

        await client.send_document(
            chat_id=message.chat.id,
            document=file_name
        )

        os.remove(file_name)

    except Exception as e:
        await msg.edit(f"❌ خطا: {e}")


# ---- اجرای Webhook + Bot ----
if __name__ == "__main__":
    import asyncio
    from threading import Thread

    def run_bot():
        bot.run()

    Thread(target=run_bot).start()

    async def set_webhook():
        async with bot:
            await bot.set_webhook(WEBHOOK_URL)

    asyncio.get_event_loop().run_until_complete(set_webhook())

    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
