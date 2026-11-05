import asyncio
import sqlite3
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart, Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo

BOT_TOKEN = "9247009785:AAEjDMvqTF9-ibXkUahTRj_5d4k7LFnQ7JQ"

# 1. TELEGRAM ID RAQAMINGIZNI YOZING:
ADMIN_TELEGRAM_ID = 7636659881  # Masalan: 564738291

# 2. VERCEL ASOSIY HAVOLASI:
MINI_APP_URL = "https://frontend-nlqlb7sq2-maverick-0331.vercel.app"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# --- BAZA BILAN ISHLASH ---
def get_db():
    conn = sqlite3.connect("academy.db")
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS leads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT NOT NULL,
            phone TEXT NOT NULL,
            email TEXT,
            course TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

# --- BOT BUYRUQLARI ---

# 1. /start - Oddiy foydalanuvchilar uchun
@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="🎓 Akademiya Ilovasini Ochish", web_app=WebAppInfo(url=MINI_APP_URL))]]
    )
    await message.answer(
        f"Salom, {message.from_user.first_name}! 👋\n\n"
        "O'quv markazimizning rasmiy platformasiga xush kelibsiz.\n"
        "Kurslarimiz va natijalar bilan tanishish uchun quyidagi tugmani bosing:",
        reply_markup=keyboard
    )

# 2. /admin - Faqat siz uchun maxsus boshqaruv
@dp.message(Command("admin"))
async def cmd_admin(message: types.Message):
    if message.from_user.id != ADMIN_TELEGRAM_ID:
        await message.answer("❌ Bu buyruq faqat markaz administratori uchun!")
        return

    conn = get_db()
    leads = conn.execute("SELECT * FROM leads ORDER BY id DESC LIMIT 10").fetchall()
    conn.close()

    if not leads:
        await message.answer("📭 Hozircha yangi arizalar yo'q.")
        return

    text = f"⚙️ <b>OXIRGI ARIZALAR ({len(leads)} ta):</b>\n\n"
    for l in leads:
        text += (
            f"🆔 #{l['id']} | 📅 {l['created_at'][:16]}\n"
            f"👤 <b>{l['full_name']}</b>\n"
            f"📞 <code>{l['phone']}</code>\n"
            f"📚 Kurs: {l['course'] or 'Umumiy'}\n"
            f"---------------------------\n"
        )
    await message.answer(text, parse_mode="HTML")

# --- FASTAPI SERVER ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    await bot.delete_webhook(drop_pending_updates=True)
    polling_task = asyncio.create_task(dp.start_polling(bot, handle_signals=False))
    print("⚡ Server va Bot 24/7 ishga tushdi...")
    yield
    polling_task.cancel()
    await bot.session.close()

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Test uchun sahifa
@app.get("/")
def home():
    return {"status": "ok", "message": "Server 24/7 ishlayapti"}

class LeadSchema(BaseModel):
    full_name: str
    phone: str
    email: str = ""
    course: str = ""

# MINI APP'DAN ARIZANI QABUL QILISH VA TELEGRAMGA XABAR YUBORISH
@app.post("/api/register")
async def create_lead(lead: LeadSchema):
    if not lead.full_name or not lead.phone:
        raise HTTPException(status_code=400, detail="Ism va telefon shart!")

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO leads (full_name, phone, email, course) VALUES (?, ?, ?, ?)",
        (lead.full_name, lead.phone, lead.email, lead.course)
    )
    conn.commit()
    new_id = cursor.lastrowid
    conn.close()

    # Adminga Telegramdan to'g'ridan-to'g'ri bildirishnoma jo'natish
    msg_text = (
        f"🔔 <b>YANGI ARIZA KELIB TUSHDI! #{new_id}</b>\n\n"
        f"👤 <b>Ism:</b> {lead.full_name}\n"
        f"📞 <b>Telefon:</b> <code>{lead.phone}</code>\n"
        f"✉️ <b>Email:</b> {lead.email or 'Kiritilmagan'}\n"
        f"📚 <b>Tanlangan Kurs:</b> {lead.course or 'Umumiy'}\n"
    )
    try:
        if ADMIN_TELEGRAM_ID:
            await bot.send_message(chat_id=ADMIN_TELEGRAM_ID, text=msg_text, parse_mode="HTML")
    except Exception as e:
        print("Xabar yuborishda xatolik:", e)

    return {"status": "success", "id": new_id}
