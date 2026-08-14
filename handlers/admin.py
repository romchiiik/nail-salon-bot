"""Админ-панель: просмотр записей, статистика, рассылка."""
import datetime as dt
import asyncio
import logging

from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

import database as db
import keyboards as kb
from config import ADMIN_IDS
from states import AdminBroadcast
from utils import format_date_human, format_price

router = Router()
logger = logging.getLogger(__name__)

# Все хендлеры в этом роутере доступны только администраторам
router.message.filter(F.from_user.id.in_(ADMIN_IDS))
router.callback_query.filter(F.from_user.id.in_(ADMIN_IDS))


@router.message(Command("admin"))
async def cmd_admin(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("🔐 Админ-панель", reply_markup=kb.admin_menu_kb())


@router.callback_query(F.data == "adm_menu")
async def cb_admin_menu(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await call.message.edit_text("🔐 Админ-панель", reply_markup=kb.admin_menu_kb())
    await call.answer()


@router.callback_query(F.data == "adm_today")
async def cb_admin_today(call: CallbackQuery):
    today = dt.date.today().isoformat()
    appts = await db.get_appointments_for_date(today)
    if not appts:
        text = "На сегодня записей нет."
    else:
        lines = [f"📋 Записи на сегодня ({len(appts)}):\n"]
        for a in appts:
            lines.append(f"{a['time']} — {a['client_name']} ({a['client_phone']})\n{a['service_name']} · {a['master_name']}\n")
        text = "\n".join(lines)
    await call.message.edit_text(text, reply_markup=kb.back_to_admin_kb())
    await call.answer()


@router.callback_query(F.data == "adm_upcoming")
async def cb_admin_upcoming(call: CallbackQuery):
    appts = await db.get_upcoming_appointments()
    if not appts:
        text = "Ближайших записей нет."
    else:
        lines = [f"📆 Ближайшие записи ({len(appts)}):\n"]
        for a in appts[:30]:
            date_obj = dt.date.fromisoformat(a["date"])
            lines.append(
                f"#{a['id']} {format_date_human(date_obj)} {a['time']} — {a['client_name']} · "
                f"{a['service_name']} ({a['master_name']})"
            )
        text = "\n".join(lines)
    await call.message.edit_text(text, reply_markup=kb.back_to_admin_kb())
    await call.answer()


@router.callback_query(F.data == "adm_stats")
async def cb_admin_stats(call: CallbackQuery):
    stats = await db.get_stats()
    text = (
        "📊 <b>Статистика</b>\n\n"
        f"Клиентов в базе: {stats['clients']}\n"
        f"Всего записей (без отмен): {stats['total_appointments']}\n"
        f"Отменено: {stats['cancelled']}\n"
        f"Выручка за текущий месяц: {format_price(stats['month_revenue'])}\n"
        f"Средний рейтинг: {stats['avg_rating'] or '—'}"
    )
    await call.message.edit_text(text, reply_markup=kb.back_to_admin_kb())
    await call.answer()


@router.callback_query(F.data == "adm_reviews")
async def cb_admin_reviews(call: CallbackQuery):
    reviews = await db.get_recent_reviews()
    if not reviews:
        text = "Отзывов пока нет."
    else:
        lines = ["⭐ Последние отзывы:\n"]
        for r in reviews:
            lines.append(
                f"{'⭐' * r['rating']} — {r['service_name']} ({r['date']})\n"
                f"{r['comment'] or '(без комментария)'}\n"
            )
        text = "\n".join(lines)
    await call.message.edit_text(text, reply_markup=kb.back_to_admin_kb())
    await call.answer()


@router.callback_query(F.data == "adm_broadcast")
async def cb_admin_broadcast_start(call: CallbackQuery, state: FSMContext):
    await state.set_state(AdminBroadcast.entering_text)
    await call.message.edit_text(
        "Введите текст сообщения для рассылки всем клиентам:",
        reply_markup=kb.back_to_admin_kb(),
    )
    await call.answer()


@router.message(AdminBroadcast.entering_text)
async def msg_admin_broadcast_text(message: Message, state: FSMContext):
    await state.update_data(broadcast_text=message.text)
    await state.set_state(AdminBroadcast.confirming)
    client_ids = await db.get_all_client_ids()
    await message.answer(
        f"Сообщение будет отправлено {len(client_ids)} клиентам:\n\n{message.text}\n\nПодтвердить?",
        reply_markup=kb.admin_broadcast_confirm_kb(),
    )


@router.callback_query(F.data == "adm_broadcast_cancel")
async def cb_admin_broadcast_cancel(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await call.message.edit_text("Рассылка отменена.", reply_markup=kb.back_to_admin_kb())
    await call.answer()


@router.callback_query(F.data == "adm_broadcast_send")
async def cb_admin_broadcast_send(call: CallbackQuery, state: FSMContext, bot: Bot):
    data = await state.get_data()
    text = data.get("broadcast_text", "")
    await state.clear()
    client_ids = await db.get_all_client_ids()

    sent, failed = 0, 0
    await call.message.edit_text("Рассылка запущена...")
    for cid in client_ids:
        try:
            await bot.send_message(cid, text)
            sent += 1
        except Exception:
            failed += 1
        await asyncio.sleep(0.05)  # избегаем rate limit Telegram

    await call.message.answer(
        f"Готово! Отправлено: {sent}, не удалось: {failed}",
        reply_markup=kb.back_to_admin_kb(),
    )
    await call.answer()
