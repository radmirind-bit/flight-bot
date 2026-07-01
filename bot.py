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
    {"from": "KZN", "to": "SHA", "name": "Казань → Шанхай", "threshold": 100000},
    {"from": "KZN", "to": "HKT", "name": "Казань → Пхукет", "threshold": 100000},
    {"from": "KZN", "to": "AYT", "name": "Казань → Анталия", "threshold": 100000},
]

async def check_prices(bot: Bot):
    async with aiohttp.ClientSession() as session:
        for route in ROUTES:
            url = "https://api.travelpayouts.com/v1/prices/cheap"
            params = {
                "origin": route["from"],
                "destination": route["to"],
                "currency": "rub",
                "token": TRAVELPAYOUTS_TOKEN,
            }
            try:
                async with session.get(url, params=params) as resp:
                    data = await resp.json()
                    if data.get("success") and data.get("data"):
                        dest = route["to"]
                        flights = data["data"].get(dest, {})
                        prices = [v["price"] for v in flights.values()]
                        if prices:
                            min_price = min(prices)
                            flight = min(flights.values(), key=lambda x: x["price"])
                            dep = flight["departure_at"][:10]
                            if min_price <= route["threshold"]:
                                msg = (
                                    f"✈️ <b>{route['name']}</b>\n"
                                    f"📅 Вылет: {dep}\n"
                                    f"💰 <b>{min_price:,} ₽</b> (порог: {route['threshold']:,} ₽)\n"
                                    f"🔗 aviasales.ru"
                                )
                                await bot.send_message(CHAT_ID, msg, parse_mode="HTML")
                                logger.info(f"Отправлено: {route['name']} — {min_price} ₽")
                        else:
                            logger.info(f"Нет данных: {route['name']}")
            except Exception as e:
                logger.error(f"Ошибка {route['name']}: {e}")
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
        "Отслеживаю:\n"
        "• Казань → Шанхай (порог 100 000 ₽)\n"
        "• Казань → Пхукет (порог 100 000 ₽)\n"
        "• Казань → Анталия (порог 100 000 ₽)\n\n"
        "Проверка каждые 6 часов.\n"
        "/check — проверить сейчас",
        parse_mode="HTML"
    )

@dp.message(Command("check"))
async def cmd_check(message: Message):
    await message.answer("🔍 Проверяю цены...")
    await check_prices(bot)
    await message.answer("✅ Готово!")

async def main():
    asyncio.create_task(price_checker_loop(bot))
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
