"""
Фоновые задачи: напоминания клиентам за 24ч/2ч до визита
и запрос отзыва после завершения записи.
Работает, пока запущен процесс бота (важно для 24/7 деплоя).
"""
import datetime as dt
import logging

from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler

import database as db
import keyboards as kb
from utils import format_date_human

logger = logging.getLogger(__name__)


async def send_reminders(bot: Bot):
    for appt in await db.get_appointments_needing_24h_reminder():
        await _send_reminder(bot, appt, "24h", "reminded_24h")

    for appt in await db.get_appointments_needing_2h_reminder():
        await _send_reminder(bot, appt, "2h", "reminded_2h")


async def _send_reminder(bot: Bot, appt: dict, kind: str, flag_field: str):
    date_obj = dt.date.fromisoformat(appt["date"])
    when = "завтра" if kind == "24h" else "уже совсем скоро"
    text = (
        f"⏰ Напоминание: {when} у вас запись в салон!\n\n"
        f"💅 {appt['service_name']}\n"
        f"👩 Мастер: {appt['master_name']}\n"
        f"📅 {format_date_human(date_obj)} в {appt['time']}"
    )
    try:
        await bot.send_message(appt["client_id"], text)
    except Exception:
        logger.exception("Не удалось отправить напоминание клиенту %s", appt["client_id"])
    finally:
        await db.mark_reminded(appt["id"], flag_field)


async def send_review_requests(bot: Bot):
    for appt in await db.get_appointments_needing_review_request():
        text = (
            "Спасибо, что посетили наш салон! 💖\n"
            f"Оцените, пожалуйста, услугу «{appt['service_name']}» у мастера {appt['master_name']}:"
        )
        try:
            await bot.send_message(appt["client_id"], text, reply_markup=kb.rating_kb(appt["id"]))
        except Exception:
            logger.exception("Не удалось отправить запрос отзыва клиенту %s", appt["client_id"])
        finally:
            await db.mark_asked_review(appt["id"])


def setup_scheduler(bot: Bot) -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler(timezone="Europe/Moscow")
    scheduler.add_job(send_reminders, "interval", minutes=30, args=[bot], id="reminders")
    scheduler.add_job(send_review_requests, "interval", minutes=60, args=[bot], id="review_requests")
    scheduler.start()
    return scheduler
