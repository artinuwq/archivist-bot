import os
import asyncio
import sqlite3
import base64
import json

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile, WebAppInfo

from config import BOT_TOKEN, CHANNEL_ID, DB_FILE

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# ----------------- База данных -----------------
def init_db():
    os.makedirs(os.path.dirname(DB_FILE), exist_ok=True)
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""
    CREATE TABLE IF NOT EXISTS files (
        message_id INTEGER PRIMARY KEY,
        file_name TEXT,
        file_type TEXT,
        size INTEGER
    )
    """)
    conn.commit()
    conn.close()

def save_file(message_id: int, file_name: str, file_type: str, size: int):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("INSERT INTO files(message_id, file_name, file_type, size) VALUES (?, ?, ?, ?)",
              (message_id, file_name, file_type, size))
    conn.commit()
    conn.close()

def list_files():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT message_id, file_name FROM files ORDER BY rowid DESC")
    rows = c.fetchall()
    conn.close()
    return rows

# ----------------- Команды -----------------
@dp.message(CommandStart())
async def start_handler(message: Message):
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[[
            InlineKeyboardButton(
                text="Открыть MiniApp",
                web_app=WebAppInfo(url="https://artinuwq.github.io/telegram-miniapp/")
            )
        ]]
    )
    await message.answer(
        "Привет!\n"
        "Используй MiniApp для работы с файлами.\n"
        "Файлы будут храниться в канале как облако.",
        reply_markup=keyboard
    )

@dp.message(Command("files"))
async def files_handler(message: Message):
    rows = list_files()
    if not rows:
        await message.reply("Файлов пока нет.")
        return

    text = "Список файлов:\n"
    for mid, name in rows:
        text += f"- {name} (id={mid})\n"
    await message.reply(text)

# ----------------- Приём файлов через MiniApp -----------------
@dp.message(F.content_type == "web_app_data")
async def webapp_file_handler(message: Message):
    try:
        data = json.loads(message.web_app_data.data)
        file_name = data['file_name']
        b64data = data['data']
        file_bytes = base64.b64decode(b64data)

        # Определяем тип файла
        ext = file_name.split('.')[-1].lower()
        if ext in ["jpg","jpeg","png","gif"]:
            file_type = "photo"
            sent = await bot.send_photo(CHANNEL_ID, FSInputFile(file_bytes))
        elif ext in ["mp4","mov","mkv"]:
            file_type = "video"
            sent = await bot.send_video(CHANNEL_ID, FSInputFile(file_bytes), caption=file_name)
        else:
            file_type = "document"
            sent = await bot.send_document(CHANNEL_ID, FSInputFile(file_bytes), caption=file_name)

        save_file(sent.message_id, file_name, file_type, len(file_bytes))
        await message.reply(f"Файл '{file_name}' успешно загружен в канал!")

    except Exception as e:
        await message.reply(f"Ошибка: {e}")

# ----------------- Скачивание файлов -----------------
@dp.message(F.text.regexp(r'^download (\d+)$'))
async def download_file_handler(message: Message):
    mid = int(message.text.split()[1])
    rows = list_files()
    target = next(((m, n) for m, n in rows if m == mid), None)
    if not target:
        await message.reply("Файл не найден!")
        return
    message_id, file_name = target
    await bot.copy_message(message.chat.id, CHANNEL_ID, message_id)

# ----------------- Main -----------------
async def main():
    init_db()
    print("Bot started")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
