from pyrogram import Client
import os

api_id = int(os.getenv("API_ID"))
api_hash = os.getenv("API_HASH")
bot_token = os.getenv("BOT_TOKEN")

print("API_ID:", api_id)
print("API_HASH:", api_hash)
print("BOT_TOKEN:", bot_token)

app = Client(
    "mybot",
    api_id=api_id,
    api_hash=api_hash,
    bot_token=bot_token
)

@app.on_message()
def reply(client, message):
    message.reply_text("ربات فعال است ✅")

app.run()
