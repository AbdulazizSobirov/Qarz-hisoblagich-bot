import asyncio
import sqlite3
from datetime import datetime
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder

API_TOKEN = "bot_token_joylashtir"

bot = Bot(API_TOKEN)
dp = Dispatcher()

# === DATABASE ===
conn = sqlite3.connect("qarzlar.db")
cursor = conn.cursor()
cursor.execute("""
CREATE TABLE IF NOT EXISTS debts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tur TEXT,
    ism TEXT,
    summa REAL,
    valyuta TEXT,
    muddat TEXT,
    sana TEXT,
    izoh TEXT
)
""")
conn.commit()

# === STATES ===
class QarzState(StatesGroup):
    tur = State()
    ism = State()
    summa = State()
    valyuta = State()
    muddat = State()
    izoh = State()

@dp.message(F.text == "/start")
async def start(message: Message, state: FSMContext):
    await state.clear()
    from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🟥 Qarz oldim"), KeyboardButton(text="🟩 Qarz berdim")],
            [KeyboardButton(text="📋 Qarzlar ro‘yxati"), KeyboardButton(text="📞 Bog‘lanish")],
        ],
        resize_keyboard=True
    )

    await message.answer("Asosiy menyu:", reply_markup=kb)

# === QARZ OLDIM ===
@dp.message(F.text.in_(["🟥 Qarz oldim", "🟩 Qarz berdim"]))
async def qarz_turi(message: Message, state: FSMContext):
    await state.update_data(tur=message.text)
    kb = ReplyKeyboardBuilder()
    kb.button(text="🏠 Bosh sahifa")
    await message.answer("Qarzni kimdan oldingiz?", reply_markup=kb.as_markup(resize_keyboard=True))
    await state.set_state(QarzState.ism)

@dp.message(QarzState.ism)
async def ism_qabul(message: Message, state: FSMContext):
    if message.text == "🏠 Bosh sahifa":
        await start(message, state)
        return
    await state.update_data(ism=message.text)
    await message.answer("Qancha summa?")
    await state.set_state(QarzState.summa)

@dp.message(QarzState.summa)
async def summa_qabul(message: Message, state: FSMContext):
    if message.text == "🏠 Bosh sahifa":
        await start(message, state)
        return
    try:
        summa = float(message.text)
    except ValueError:
        await message.answer("Iltimos, son kiriting!")
        return
    await state.update_data(summa=summa)

    kb = InlineKeyboardBuilder()
    for val in ["UZS", "USD", "RUBL"]:
        kb.button(text=val, callback_data=val)
    await message.answer("Qaysi valyutada?", reply_markup=kb.as_markup())

@dp.callback_query(F.data.in_(["UZS", "USD", "RUBL"]))
async def valyuta_qabul(callback: CallbackQuery, state: FSMContext):
    await state.update_data(valyuta=callback.data)
    await callback.message.answer("Qaysi muddatgacha (YYYY-MM-DD formatda)?")
    await state.set_state(QarzState.muddat)
    await callback.answer()

@dp.message(QarzState.muddat)
async def muddat_qabul(message: Message, state: FSMContext):
    if message.text == "🏠 Bosh sahifa":
        await start(message, state)
        return
    await state.update_data(muddat=message.text)
    await message.answer("Izoh kiriting (yoki 'yo‘q' deb yozing):")
    await state.set_state(QarzState.izoh)

@dp.message(QarzState.izoh)
async def izoh_qabul(message: Message, state: FSMContext):
    data = await state.get_data()
    tur = data['tur']
    ism = data['ism']
    summa = data['summa']
    valyuta = data['valyuta']
    muddat = data['muddat']
    izoh = message.text
    sana = datetime.now().strftime("%Y-%m-%d")

    cursor.execute("INSERT INTO debts (tur, ism, summa, valyuta, muddat, sana, izoh) VALUES (?, ?, ?, ?, ?, ?, ?)",
                   (tur, ism, summa, valyuta, muddat, sana, izoh))
    conn.commit()

    await message.answer(f"✅ Qarz saqlandi!\n\n"
                         f"💬 {tur}\n👤 {ism}\n💰 {summa} {valyuta}\n📅 Muddat: {muddat}\n🕒 Sana: {sana}")
    await start(message, state)

# === QARZLAR RO‘YXATI ===
@dp.message(F.text == "📋 Qarzlar ro‘yxati")
async def qarzlar_royxati(message: Message):
    cursor.execute("SELECT id, tur, ism, summa, valyuta, muddat FROM debts")
    qarzlar = cursor.fetchall()
    if not qarzlar:
        await message.answer("📭 Qarzlar mavjud emas.")
        return
    for qarz in qarzlar:
        id, tur, ism, summa, valyuta, muddat = qarz
        kb = InlineKeyboardBuilder()
        kb.button(text="✅ To‘landi", callback_data=f"del_{id}")
        await message.answer(
            f"{tur}\n👤 {ism}\n💰 {summa} {valyuta}\n📅 Muddat: {muddat}",
            reply_markup=kb.as_markup()
        )

# === QARZNI O‘CHIRISH ===
@dp.callback_query(F.data.startswith("del_"))
async def qarz_tolandi(callback: CallbackQuery):
    qarz_id = callback.data.split("_")[1]
    cursor.execute("DELETE FROM debts WHERE id=?", (qarz_id,))
    conn.commit()
    await callback.message.answer("✅ Qarz to‘landi va o‘chirildi.")
    await callback.answer()

@dp.message(F.text == "📞 Bog‘lanish")
async def boglanish(message: Message):
    await message.answer(
        "📞 Aloqa uchun: @silence_offf\n"
        "📧 Pochta: Uzstarsxtv@gmail.com"
    )

# === MAIN ===
async def main():
    print("Bot ishga tushdi...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
