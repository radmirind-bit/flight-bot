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
    {"from": "KZN", "to": "SHA", "name": "Казань - Шанхай", "threshold": 23000},
    {"from": "KZN", "to": "HKT", "name": "Казань - Пхукет", "threshold": 25000},
    {"from": "KZN", "to": "AYT", "name": "Казань - Анталия", "threshold": 10000},
]

MONTHS = ["2026-07", "2026-08", "2026-09", "2026-10", "2026-11"]
MONTH_NAMES = {
    "2026-07": "Июль", "2026-08": "Август", "2026-09": "Сентябрь",
    "2026-10": "Октябрь", "2026-11": "Ноябрь"
}

async def check_prices(bot: Bot):
    found_any = False
    async with aiohttp.ClientSession() as session:
        for route in ROUTES:
            for month in MONTHS:
                url = "https://api.travelpayouts.com/v2/prices/latest"
                params = {
                    "origin": route["from"],
                    "destination": route["to"],
                    "currency": "rub",
                    "token": TRAVELPAYOUTS_TOKEN,
                    "limit": 30,
                    "sorting": "price",
                    "period_type": "month",
                    "one_way": "true",
                    "beginning_of_period": month + "-01",
                }
                try:
                    async with session.get(url, params=params) as resp:
                        data = await resp.json()
                        if data.get("success") and data.get("data"):
                            flights = [
                                f for f in data["data"]
                                if f.get("depart_date", "").startswith(month)
                                and f.get("actual", False)
                            ]
                            if flights:
                                best = min(flights, key=lambda x: x["value"])
                                price = best["value"]
                                dep = best["depart_date"]
                                gate = best.get("gate", "")
                                logger.info(route["name"] + " " + MONTH_NAMES[month] + ": " + str(price) + " руб (" + gate + ")")
                                if price <= route["threshold"]:
                                    found_any = True
                                    msg = (
                                        route["name"] + "\n"
                                        + MONTH_NAMES[month] + " - вылет " + dep + "\n"
                                        + str(price) + " руб (порог: " + str(route["threshold"]) + " руб)\n"
                                        + "Через: " + gate
                                    )
                                    await bot.send_message(CHAT_ID, msg)
                except Exception as e:
                    logger.error("Ошибка " + route["name"] + " " + month + ": " + str(e))
                await asyncio.sleep(1)
    return found_any

async def price_checker_loop(bot: Bot):
    while True:
        await check_prices(bot)
        await asyncio.sleep(6 * 60 * 60)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

@dp.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer(
        "Трекер запущен!\n\n"
        "Отслеживаю июль-ноябрь 2026:\n"
        "Казань - Шанхай (порог 23000 руб)\n"
        "Казань - Пхукет (порог 25000 руб)\n"
        "Казань - Анталия (порог 10000 руб)\n\n"
        "Проверка каждые 6 часов.\n"
        "/check - проверить сейчас"
    )

@dp.message(Command("check"))
async def cmd_check(message: Message):
    await message.answer("Проверяю цены...")
    found = await check_prices(bot)
    if not found:
        await message.answer("Готово. Цен ниже порога не найдено.")
    else:
        await message.answer("Готово! Уведомления отправлены.")

async def main():
    asyncio.create_task(price_checker_loop(bot))
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
