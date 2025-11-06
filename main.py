import os
import asyncio
import random
import sqlite3
import datetime
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import CommandStart
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, BotCommand
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.client.bot import DefaultBotProperties
from dotenv import load_dotenv
from PIL import Image, ImageDraw, ImageFont
import io

# 🔹 Tokenni olish (.env dan)
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

# 🔹 Botni yaratish
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"), session=AiohttpSession())
dp = Dispatcher()

# 🔹 Ma’lumotlar bazasi
conn = sqlite3.connect("farosat.db")
cursor = conn.cursor()

# Foydalanuvchilar jadvali
cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    username TEXT
)
""")

# Farosat logi: har bir user + har bir chat
cursor.execute("""
CREATE TABLE IF NOT EXISTS farosat_log (
    user_id INTEGER,
    chat_id INTEGER,
    farosat INTEGER DEFAULT 0,
    last_farosat_date TEXT,
    PRIMARY KEY (user_id, chat_id)
)
""")
conn.commit()

# 🔹 Foydalanuvchini bazaga qo‘shish
def register_user(user_id: int, username: str):
    cursor.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
    if cursor.fetchone() is None:
        cursor.execute("INSERT INTO users (user_id, username) VALUES (?, ?)", (user_id, username))
        conn.commit()

# 🔹 /add_farosat (faqat admin uchun)
ADMIN_ID = 7160923142  # <-- o'zingizning telegram ID

@dp.message(F.text.regexp(r"^/add_farosat(@\w+)?\s+\d+\s+\d+$"))
async def add_farosat_handler(message: types.Message):
    user_id = message.from_user.id
    if user_id != ADMIN_ID:
        await message.reply("❌ Bu komanda faqat admin uchun!")
        return

    try:
        parts = message.text.split()
        target_user_id = int(parts[1])
        amount = int(parts[2])

        cursor.execute("SELECT farosat FROM farosat_log WHERE user_id=? AND chat_id=?", (target_user_id, message.chat.id))
        result = cursor.fetchone()
        if result is None:
            # Agar log mavjud bo‘lmasa yaratamiz
            cursor.execute("INSERT INTO farosat_log (user_id, chat_id, farosat, last_farosat_date) VALUES (?, ?, ?, ?)",
                           (target_user_id, message.chat.id, amount, None))
            conn.commit()
            await message.reply(f"✅ Foydalanuvchiga {amount} farosat qo‘shildi! Jami: {amount} gram")
            return

        new_value = result[0] + amount
        cursor.execute("UPDATE farosat_log SET farosat=? WHERE user_id=? AND chat_id=?", (new_value, target_user_id, message.chat.id))
        conn.commit()
        await message.reply(f"✅ Foydalanuvchiga {amount} farosat qo‘shildi! Jami: {new_value} gram")
    except Exception as e:
        await message.reply(f"❌ Xatolik: {e}")

# 🔹 Komandalar menyusi
async def set_commands(bot: Bot):
    commands = [
        BotCommand(command="start", description="Botni ishga tushirish"),
        BotCommand(command="help", description="Yordam"),
        BotCommand(command="farosat", description="Farosat olish 🧠"),
        BotCommand(command="top10", description="Chat Top-10 🏆"),
        BotCommand(command="worldtop10", description="Dunyodagi Top-10 🌍"),
        BotCommand(command="pic_farosat", description="Rasmda farosat 🌠️"),
        BotCommand(command="mycertificate", description="Sertifikat 🎖️"),
    ]
    await bot.set_my_commands(commands)

# 🔹 /start
@dp.message(CommandStart())
async def start_handler(message: types.Message):
    user = message.from_user
    register_user(user.id, user.username or user.full_name)

    bot_info = await bot.get_me()
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Guruhga qo‘shish", url=f"https://t.me/{bot_info.username}?startgroup=true")]
    ])

    text = (
        f"- Hello, <b>{user.full_name}</b>! 🖖\n"
        "👨🏾‍🍳 Men gruhlar uchun <b>Farosatchi</b>.\n\n"
        "Savollar bo‘lsa: /help komandasini yozing!"
    )

    await message.answer(text, reply_markup=keyboard)

# 🔹 /help
@dp.message(F.text.regexp(r"^/help(@\w+)?$"))
async def help_handler(message: types.Message):
    text = (
        "🎗️ <b>Botning komandalari:</b>\n\n"
        "/farosat - Farosatni o‘stirish 🧠\n"
        "/top10 - Chat Top-10 🏆\n"
        "/worldtop10 - Dunyodagi Top-10 🌍\n"
        "/pic_farosat - Rasmda farosat 🌠️\n"
        "/mycertificate - Sertifikat 🎖️"
    )
    await message.answer(text)

# 🔹 /farosat (har bir guruh uchun alohida)
@dp.message(F.text.regexp(r"^/farosat(@\w+)?$"))
async def farosat_handler(message: types.Message):
    user = message.from_user
    chat_id = message.chat.id
    register_user(user.id, user.username or user.full_name)

    today = datetime.date.today().isoformat()
    cursor.execute("SELECT farosat, last_farosat_date FROM farosat_log WHERE user_id=? AND chat_id=?", (user.id, chat_id))
    result = cursor.fetchone()

    if result:
        farosat_value, last_date = result
    else:
        farosat_value, last_date = 0, None
        cursor.execute("INSERT INTO farosat_log (user_id, chat_id, farosat, last_farosat_date) VALUES (?, ?, ?, ?)",
                       (user.id, chat_id, 0, None))
        conn.commit()

    if last_date == today:
        await message.reply("🕛 Siz bugun bu guruhda farosat oldingiz, boshqa guruhda yana urinib ko‘ring.")
        return

    delta = random.randint(-5, 20)
    farosat_value += delta
    cursor.execute("UPDATE farosat_log SET farosat=?, last_farosat_date=? WHERE user_id=? AND chat_id=?", (farosat_value, today, user.id, chat_id))
    conn.commit()

    if delta >= 0:
        msg = f"🧠 Sizga bugun <b>+{delta} gram</b> farosat qo‘shildi!\nJami bu guruhda: <b>{farosat_value} gram</b>"
    else:
        msg = f"😅 Sizdan bugun <b>{delta} gram</b> farosat ketdi!\nJami bu guruhda: <b>{farosat_value} gram</b>"

    await message.reply(msg)

# 🔹 /top10 (chat bo‘yicha)
@dp.message(F.text.regexp(r"^/top10(@\w+)?$"))
async def top10_handler(message: types.Message):
    chat_id = message.chat.id
    cursor.execute("SELECT u.username, f.farosat FROM farosat_log f JOIN users u ON f.user_id=u.user_id WHERE f.chat_id=? ORDER BY f.farosat DESC LIMIT 10", (chat_id,))
    top_users = cursor.fetchall()

    text = "🏆 <b>Chat Top-10 Farosatchilar:</b>\n\n"
    for i, user in enumerate(top_users, start=1):
        name = user[0] or "Anonim"
        text += f"{i}. {name} — {user[1]} gram\n"
    await message.answer(text)

# 🔹 /worldtop10 (dunyo bo‘yicha)
@dp.message(F.text.regexp(r"^/worldtop10(@\w+)?$"))
async def world_top10_handler(message: types.Message):
    cursor.execute("SELECT u.username, SUM(f.farosat) FROM farosat_log f JOIN users u ON f.user_id=u.user_id GROUP BY f.user_id ORDER BY SUM(f.farosat) DESC LIMIT 10")
    rows = cursor.fetchall()

    text = "🌍 <b>Dunyodagi Top-10 Farosatchilar:</b>\n\n"
    for i, (name, grams) in enumerate(rows, start=1):
        name = name or "Anonim"
        text += f"{i}. {name} — {grams} gram\n"
    await message.answer(text)

# 🔹 /pic_farosat
@dp.message(F.text.regexp(r"^/pic_farosat(@\w+)?$"))
async def pic_farosat_handler(message: types.Message):
    user = message.from_user
    chat_id = message.chat.id
    cursor.execute("SELECT farosat FROM farosat_log WHERE user_id=? AND chat_id=?", (user.id, chat_id))
    result = cursor.fetchone()
    farosat_value = result[0] if result else 0

    img = Image.new('RGB', (500, 300), color=(30, 40, 80))
    draw = ImageDraw.Draw(img)
    font = ImageFont.load_default()
    draw.text((20, 50), f"{user.full_name}", fill=(255, 255, 0), font=font)
    draw.text((20, 120), f"Farosat: {farosat_value} gram", fill=(255, 255, 255), font=font)

    bio = io.BytesIO()
    bio.name = 'farosat.png'
    img.save(bio, 'PNG')
    bio.seek(0)
    await message.answer_photo(photo=types.InputFile(bio))

# 🔹 /mycertificate
@dp.message(F.text.regexp(r"^/mycertificate(@\w+)?$"))
async def certificate_handler(message: types.Message):
    user = message.from_user
    chat_id = message.chat.id
    cursor.execute("SELECT farosat FROM farosat_log WHERE user_id=? AND chat_id=?", (user.id, chat_id))
    result = cursor.fetchone()
    farosat_value = result[0] if result else 0

    img = Image.new('RGB', (600, 400), color=(220, 200, 160))
    draw = ImageDraw.Draw(img)
    font = ImageFont.load_default()
    draw.text((50, 100), "🏅 SERTIFIKAT 🏅", fill=(0, 0, 0), font=font)
    draw.text((50, 180), f"{user.full_name}", fill=(0, 0, 0), font=font)
    draw.text((50, 250), f"Farosat: {farosat_value} gram", fill=(0, 0, 0), font=font)

    bio = io.BytesIO()
    bio.name = 'certificate.png'
    img.save(bio, 'PNG')
    bio.seek(0)
    await message.answer_photo(photo=types.InputFile(bio))

# 🔹 Botni ishga tushirish
async def main():
    await set_commands(bot)
    print("🤖 FarosatGram Bot ishga tushdi...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
