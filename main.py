import asyncio
import sqlite3
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo

BOT_TOKEN = "9247009785:AAEjDMvqTF9-ibXkUahTRj_5d4k7LFnQ7JQ"
MINI_APP_URL = "https://frontend-frzci9py5-maverick-0331.vercel.app"

# ==============================================================
# BU YERGA TELEGRAM ID RAQAMINGIZNI YOZING:
ADMIN_TELEGRAM_ID = 7636659881  # Masalan: 564738291
# ==============================================================

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

def get_db():
    conn = sqlite3.connect("academy.db")
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS registrations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT,
            phone TEXT,
            email TEXT,
            course TEXT,
            date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

class RegisterModel(BaseModel):
    full_name: str
    phone: str
    email: str = ""
    course: str = ""

@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="🎓 Akademiya Ilovasini Ochish", web_app=WebAppInfo(url=MINI_APP_URL))]]
    )
    await message.answer(
        f"Salom, {message.from_user.first_name}! 👋\n"
        "O'quv markazimizning rasmiy platformasiga xush kelibsiz.\n"
        "Ilovani ochish uchun pastdagi tugmani bosing:",
        reply_markup=keyboard
    )

async def start_bot():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot, handle_signals=False)

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    print("⚡ Bot va Baza 24/7 ishga tushdi...")
    polling_task = asyncio.create_task(start_bot())
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

@app.get("/")
def health():
    return {"status": "ok", "bot": "running 24/7"}

# TALABALAR ARIZASINI QABUL QILISH VA TELEGRAMGA XABAR YUBORISH
@app.post("/api/register")
async def register_lead(reg: RegisterModel):
    conn = get_db()
    conn.execute("INSERT INTO registrations (full_name, phone, email, course) VALUES (?, ?, ?, ?)",
                 (reg.full_name, reg.phone, reg.email, reg.course))
    conn.commit()
    conn.close()

    # Adminga shaxsiy xabar yuborish
    msg = (
        f"🔔 YANGI ARIZA KELIB TUSHDI!\n\n"
        f"👤 Ism: {reg.full_name}\n"
        f"📞 Tel: {reg.phone}\n"
        f"✉️ Email: {reg.email or 'Kiritilmagan'}\n"
        f"📚 Kurs: {reg.course or 'Umumiy'}\n"
    )
    try:
        if ADMIN_TELEGRAM_ID and ADMIN_TELEGRAM_ID != 123456789:
            await bot.send_message(chat_id=ADMIN_TELEGRAM_ID, text=msg)
    except Exception as e:
        print("Xabar yuborishda xatolik:", e)

    return {"status": "ok"}

# ADMIN UCHUN BARCHA ARIZALAR RO'YXATI
@app.get("/api/admin/registrations")
def get_leads():
    conn = get_db()
    leads = [dict(row) for row in conn.execute("SELECT * FROM registrations ORDER BY id DESC").fetchall()]
    conn.close()
    return leads

@app.delete("/api/admin/registrations/{lead_id}")
def delete_lead(lead_id: int):
    conn = get_db()
    conn.execute("DELETE FROM registrations WHERE id = ?", (lead_id,))
    conn.commit()
    conn.close()
    return {"status": "deleted"}
