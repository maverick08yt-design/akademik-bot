import asyncio
import sqlite3
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart, Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo

BOT_TOKEN = "9247009785:AAEjDMvqTF9-ibXkUahTRj_5d4k7LFnQ7JQ"

# SIZNING ANIQ TELEGRAM ID RAQAMINGIZ:
ADMIN_TELEGRAM_ID = 7636659881

# Vercel havolangiz:
MINI_APP_URL = "https://frontend-8p948oybp-maverick-0331.vercel.app"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

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

@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="Akademiya Ilovasini Ochish", web_app=WebAppInfo(url=MINI_APP_URL))]]
    )
    await message.answer(
        f"Assalomu alaykum, {message.from_user.first_name}!\n\n"
        "O'quv markazimizning rasmiy platformasiga xush kelibsiz.\n"
        "Kurslar bilan tanishish uchun quyidagi tugmani bosing:",
        reply_markup=keyboard
    )

# Faqat ID: 7636659881 yozgandagina ishlaydi:
@dp.message(Command("admin"))
async def cmd_admin(message: types.Message):
    if message.from_user.id != ADMIN_TELEGRAM_ID:
        return

    conn = get_db()
    leads = conn.execute("SELECT * FROM leads ORDER BY id DESC LIMIT 15").fetchall()
    conn.close()

    if not leads:
        await message.answer("Hozircha arizalar mavjud emas.")
        return

    text = f"<b>Kelib tushgan arizalar ({len(leads)} ta):</b>\n\n"
    for l in leads:
        text += (
            f"ID #{l['id']} | {l['created_at'][:16]}\n"
            f"F.I.O: {l['full_name']}\n"
            f"Telefon: <code>{l['phone']}</code>\n"
            f"Kurs: {l['course'] or 'Umumiy'}\n"
            f"---------------------------\n"
        )
    await message.answer(text, parse_mode="HTML")

async def start_bot():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot, handle_signals=False)

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
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
def home():
    return {"status": "ok", "message": "Server 24/7 ishlamoqda"}

class LeadSchema(BaseModel):
    full_name: str
    phone: str
    email: str = ""
    course: str = ""

@app.post("/api/register")
async def create_lead(lead: LeadSchema):
    if not lead.full_name or not lead.phone:
        raise HTTPException(status_code=400, detail="Ism va telefon kiritilishi shart.")

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO leads (full_name, phone, email, course) VALUES (?, ?, ?, ?)",
        (lead.full_name, lead.phone, lead.email, lead.course)
    )
    conn.commit()
    new_id = cursor.lastrowid
    conn.close()

    # Xabar to'g'ridan-to'g'ri 7636659881 ID profiliga yuboriladi:
    msg_text = (
        f"<b>YANGI ARIZA QABUL QILINDI #{new_id}</b>\n\n"
        f"F.I.O: {lead.full_name}\n"
        f"Telefon: <code>{lead.phone}</code>\n"
        f"Elektron pochta: {lead.email or 'Kiritilmagan'}\n"
        f"Kurs: {lead.course or 'Umumiy'}\n"
    )
    try:
        await bot.send_message(chat_id=ADMIN_TELEGRAM_ID, text=msg_text, parse_mode="HTML")
    except Exception as e:
        print("Telegramga yuborishda xatolik:", e)

    return {"status": "success", "id": new_id}

@app.get("/api/admin/registrations")
def get_leads():
    conn = get_db()
    leads = [dict(row) for row in conn.execute("SELECT * FROM leads ORDER BY id DESC").fetchall()]
    conn.close()
    return leads

@app.delete("/api/admin/registrations/{lead_id}")
def delete_lead(lead_id: int):
    conn = get_db()
    conn.execute("DELETE FROM leads WHERE id = ?", (lead_id,))
    conn.commit()
    conn.close()
    return {"status": "deleted"}
