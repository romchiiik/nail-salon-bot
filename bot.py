"""
Telegram-бот для записи в маникюрный салон.
Точка входа: запускает polling, инициализирует БД и планировщик напоминаний.
"""
import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from config import BOT_TOKEN
import database as db
from scheduler import setup_scheduler
from handlers import client, admin, reviews

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


async def main():
    await db.init_db()
    logger.info("База данных готова")

    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher(storage=MemoryStorage())

    # Порядок важен: admin-роутер первым, чтобы админ-команды не перехватывались клиентскими
    dp.include_router(admin.router)
    dp.include_router(reviews.router)
    dp.include_router(client.router)

    scheduler = setup_scheduler(bot)
    logger.info("Планировщик напоминаний запущен")

    try:
        await bot.delete_webhook(drop_pending_updates=True)
        logger.info("Бот запущен, начинаем polling...")
        await dp.start_polling(bot)
    finally:
        scheduler.shutdown()
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Бот остановлен")
