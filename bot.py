import asyncio
import logging
import os
import aiohttp
from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.types import Message

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")
TRAVELPAYOUTS_TOKEN = os.getenv("TRAVELPAYOUTS_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

ROUTES = [
    {"from": "KZN", "to": "SHA", "name": "Казань → Шанхай", "threshold": 25000},
    {"from": "KZN", "to": "HKT", "name": "Казань → Пхукет", "threshold": 25000},
    {"from": "KZN", "to": "AYT", "name": "Казань → Анталия", "threshold": 25000},
]

MONTHS = ["2026-07", "2026-08", "2026-09", "2026-10", "2026-11"]
MONTH_NAMES = {
    "2026-07": "Июль", "2026-08": "Август", "2026-09": "Сентябрь",
    "2026-10": "Октябрь", "2026-11": "Ноябрь"
}

async def check_prices(bot: Bot):
    async with aiohttp.ClientSession() as session:
        for route in ROUTES:
            for month in MONTHS:
                url = "https://api.travelpayouts.com/v1/prices/cheap"
                params = {
                    "origin": route["from"],
                    "destination": route["to"],
                    "depart_date": month,
                    "currency": "rub",
                    "token": TRAVELPAYOUTS_TOKEN,
                }
                try:
                    async with session.get(url, params=params) as resp:
                        data = await resp.json()
                        if data.get("success") and data.get("data"):
                            dest = route["to"]
                            flights = data["data"].get(dest, {})
                            if flights:
                                flight = min(flights.values(), key=lambda x: x["price"])
                                min_price = flight["price"]
                                dep = flight["departure_at"][:10]
                                logger.info(f"{route['name']} {MONTH_NAMES[month]}: {min_price} ₽")
                                if min_price <= route["threshold"]:
                                    msg = (
                                        f"✈️ <b>{route['name']}</b>\n"
                                        f"📅 {MONTH_NAMES[month]} · вылет {dep}\n"
                                        f"💰 <b>{min_price:,} ₽</b> (порог: {route['threshold']:,} ₽)\n"
                                        f"🔗 aviasales.ru"
                                    )
                                    await bot.send_message(CHAT_ID, msg, parse_mode="HTML")
                except Exception as e:
                    logger.error(f"Ошибка {route['name']} {month}: {e}")
                await asyncio.sleep(1)

async def price_checker_loop(bot: Bot):
    while True:
        await check_prices(bot)
        await asyncio.sleep(6 * 60 * 60)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

@dp.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer(
        "✈️ <b>Трекер запущен!</b>\n\n"
        "Отслеживаю июль–ноябрь 2026:\n"
        "• Казань → Шанхай (порог 25 000 ₽)\n"
        "• Казань → Пхукет (порог 25 000 ₽)\n"
        "• Казань → Анталия (порог 25 000 ₽)\n\n"
        "Проверка каждые 6 часов.\n"
        "/check — проверить сейчас",
        parse_mode="HTML"
    )

@dp.message(Command("check"))
async def cmd_check(message: Message):
    await message.answer("🔍 Проверяю цены по всем месяцам...")
    await check_prices(bot)
    await message.answer("✅ Готово!")

async def main():
    asyncio.create_task(price_checker_loop(bot))
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
