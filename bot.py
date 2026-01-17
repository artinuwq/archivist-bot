import os
import asyncio
import sqlite3
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile, WebAppInfo

from config import BOT_TOKEN, CHANNEL_ID, ALLOWED_USER_IDS, OBSIDIAN_PATH, DOWNLOAD_DIR, KEEP_TIKTOK_FILES

DB_FILE = "files.db"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# ----------------- База данных -----------------
def init_db():
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
    await message.answer(
        "Привет!\n"
        "- Используй MiniApp для работы с файлами.\n"
        "- Файлы будут храниться в канале как облако."
    )

# ----------------- Приём файлов через MiniApp -----------------
@dp.message(F.content_type.in_({"document", "video", "photo"}))
async def upload_handler(message: Message):
    file = message.document or message.video or (message.photo[-1] if message.photo else None)
    if not file:
        await message.reply("Файл не найден!")
        return

    # Отправка файла в канал
    if message.document:
        sent = await bot.send_document(CHANNEL_ID, message.document.file_id, caption=message.document.file_name)
        file_name = message.document.file_name
        file_type = "document"
        size = message.document.file_size
    elif message.video:
        sent = await bot.send_video(CHANNEL_ID, message.video.file_id, caption=message.video.file_name or "video.mp4")
        file_name = message.video.file_name or "video.mp4"
        file_type = "video"
        size = message.video.file_size
    elif message.photo:
        sent = await bot.send_photo(CHANNEL_ID, message.photo[-1].file_id)
        file_name = "photo.jpg"
        file_type = "photo"
        size = message.photo[-1].file_size

    # Сохраняем в БД
    save_file(sent.message_id, file_name, file_type, size)
    await message.reply(f"Файл '{file_name}' успешно загружен!")

# ----------------- Список файлов -----------------
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

@dp.message(Command("ui"))
async def ui_handler(message: Message):
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Открыть MiniApp",
                    web_app=WebAppInfo(url="https://artinuwq.github.io/telegram-miniapp/")
                )
            ]
        ]
    )
    await message.answer("Открываю MiniApp:", reply_markup=keyboard)

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
