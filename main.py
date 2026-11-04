import asyncio
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo

BOT_TOKEN = "9247009785:AAEjDMvqTF9-ibXkUahTRj_5d4k7LFnQ7JQ"
MINI_APP_URL = "https://frontend-frzci9py5-maverick-0331.vercel.app"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Bot /start buyrug'i
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

# FastAPI ishga tushganda Bot ham orqa fonda yonadi
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("⚡ Bot 24/7 polling rejimida ishga tushdi...")
    polling_task = asyncio.create_task(dp.start_polling(bot))
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

# Server ishlab turganini tekshirish uchun oyna
@app.get("/")
def health_check():
    return {"status": "ok", "bot": "24/7 running"}