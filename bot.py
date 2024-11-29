from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from pymongo import MongoClient
from script import WELCOME_MESSAGE, NO_RESULTS_MESSAGE, FILE_NOT_FOUND_MESSAGE, CHANNEL_ID

BOT_TOKEN = "7806693412:AAEUlgurG0t41lsMDZ75GvE4DgDcwQU9qbY"
API_ID = "24870301"
API_HASH = "5bcc6d5a90ad19da0989d635a36942af"
MONGO_URI = "mongodb+srv://bitget:20030928@cluster0.jk909.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"

# Initialize the bot and database
app = Client("AutoFilterBot", bot_token=BOT_TOKEN, api_id=API_ID, api_hash=API_HASH)
client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
db = client["telegram_files"]
collection = db["files"]


try:
    client.server_info()  
    print("MongoDB connected successfully!")
except Exception as e:
    print(f"Failed to connect to MongoDB: {e}")
    exit()

@app.on_message(filters.private & filters.command("start"))
async def welcome(client, message):
    await message.reply(WELCOME_MESSAGE)

@app.on_message(filters.channel & (filters.document | filters.video | filters.audio))
async def save_files(client, message):
    file_id = message.document.file_id if message.document else (
        message.video.file_id if message.video else message.audio.file_id
    )
    file_name = message.document.file_name if message.document else (
        message.video.file_name if message.video else message.audio.file_name
    )
    file_data = {
        "file_id": file_id,
        "file_name": file_name,
        "channel_id": message.chat.id,
        "message_id": message.id,
    }
    collection.update_one({"file_id": file_id}, {"$set": file_data}, upsert=True)

@app.on_message(filters.private & filters.text)
async def search_files(client, message):
    query = message.text.strip()
    results = collection.find({"file_name": {"$regex": query, "$options": "i"}})
    files = list(results)
    if not files:
        await message.reply(NO_RESULTS_MESSAGE)
        return
    buttons = [
        [InlineKeyboardButton(file["file_name"], callback_data=file["file_id"])]
        for file in files
    ]
    reply_markup = InlineKeyboardMarkup(buttons)
    await message.reply("Search Results:", reply_markup=reply_markup)

@app.on_callback_query()
async def send_file(client, callback_query):
    file_id = callback_query.data
    file = collection.find_one({"file_id": file_id})
    if not file:
        await callback_query.message.edit(FILE_NOT_FOUND_MESSAGE)
        return
    await callback_query.message.reply_document(
        document=file["file_id"], caption=f"Here is your file: {file['file_name']}"
    )

@app.on_startup
async def fetch_old_files(client):
    async for message in client.iter_history(CHANNEL_ID):
        if message.document or message.video or message.audio:
            file_id = message.document.file_id if message.document else (
                message.video.file_id if message.video else message.audio.file_id
            )
            file_name = message.document.file_name if message.document else (
                message.video.file_name if message.video else message.audio.file_name
            )
            file_data = {
                "file_id": file_id,
                "file_name": file_name,
                "channel_id": message.chat.id,
                "message_id": message.id,
            }
            collection.update_one({"file_id": file_id}, {"$set": file_data}, upsert=True)

if __name__ == "__main__":
    app.run()
