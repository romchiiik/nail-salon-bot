"""Хендлеры для клиентов: главное меню, запись, мои записи, история, отмена/перенос."""
import datetime as dt
import logging

from aiogram import Router, F, Bot
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

import database as db
import keyboards as kb
from config import SALON_NAME, ADMIN_IDS
from states import Booking, Rescheduling
from utils import available_dates, format_date_human, format_price, format_duration, generate_time_slots

router = Router()
logger = logging.getLogger(__name__)


async def show_main_menu(message: Message, greet: bool = True):
    text = (
        f"💅 <b>{SALON_NAME}</b>\n\n"
        "Здесь вы можете записаться на маникюр или педикюр, "
        "посмотреть свои записи и историю визитов.\n\n"
        "Выберите действие:"
    ) if greet else "Выберите действие:"
    await message.answer(text, reply_markup=kb.main_menu_kb())


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    await db.upsert_client(message.from_user.id, name=message.from_user.full_name)
    await show_main_menu(message)


@router.message(Command("menu"))
async def cmd_menu(message: Message, state: FSMContext):
    await state.clear()
    await show_main_menu(message)


@router.callback_query(F.data == "back_to_menu")
async def cb_back_to_menu(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await call.message.edit_text("Выберите действие:", reply_markup=kb.main_menu_kb())
    await call.answer()


# ---------------- Контакты ----------------

@router.callback_query(F.data == "contacts")
async def cb_contacts(call: CallbackQuery):
    text = (
        f"📍 <b>{SALON_NAME}</b>\n\n"
        "Адрес: ул. Примерная, 10\n"
        "Часы работы: 10:00 – 20:00, ежедневно\n"
        "Телефон: +7 (999) 123-45-67\n\n"
        "Это демо-бот, созданный для портфолио 🙂"
    )
    kb_back = kb.InlineKeyboardBuilder()
    kb_back.button(text="⬅️ Назад", callback_data="back_to_menu")
    await call.message.edit_text(text, reply_markup=kb_back.as_markup())
    await call.answer()


# ---------------- Запись: выбор категории/услуги ----------------

@router.callback_query(F.data == "book")
async def cb_book(call: CallbackQuery, state: FSMContext):
    services = await db.get_services()
    categories = sorted({s["category"] for s in services})
    await state.set_state(Booking.choosing_category)
    await call.message.edit_text("Выберите категорию услуг:", reply_markup=kb.categories_kb(categories))
    await call.answer()


@router.callback_query(F.data == "back_to_categories", Booking.choosing_service)
async def cb_back_to_categories(call: CallbackQuery, state: FSMContext):
    await cb_book(call, state)


@router.callback_query(F.data.startswith("cat:"), Booking.choosing_category)
async def cb_choose_category(call: CallbackQuery, state: FSMContext):
    category = call.data.split(":", 1)[1]
    await state.update_data(category=category)
    services = [s for s in await db.get_services() if s["category"] == category]
    await state.set_state(Booking.choosing_service)
    await call.message.edit_text(f"Категория: {category}\nВыберите услугу:", reply_markup=kb.services_kb(services))
    await call.answer()


@router.callback_query(F.data.startswith("service:"), Booking.choosing_service)
async def cb_choose_service(call: CallbackQuery, state: FSMContext):
    service_id = int(call.data.split(":", 1)[1])
    service = await db.get_service(service_id)
    await state.update_data(service_id=service_id)
    masters = await db.get_masters()
    await state.set_state(Booking.choosing_master)
    text = (
        f"Услуга: <b>{service['name']}</b>\n"
        f"Цена: {format_price(service['price'])}, длительность: {format_duration(service['duration_minutes'])}\n\n"
        "Выберите мастера:"
    )
    await call.message.edit_text(text, reply_markup=kb.masters_kb(masters))
    await call.answer()


@router.callback_query(F.data == "back_to_services", Booking.choosing_master)
async def cb_back_to_services(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    services = [s for s in await db.get_services() if s["category"] == data.get("category")]
    await state.set_state(Booking.choosing_service)
    await call.message.edit_text("Выберите услугу:", reply_markup=kb.services_kb(services))
    await call.answer()


@router.callback_query(F.data.startswith("master:"), Booking.choosing_master)
async def cb_choose_master(call: CallbackQuery, state: FSMContext):
    master_id = int(call.data.split(":", 1)[1])
    master = await db.get_master(master_id)
    await state.update_data(master_id=master_id)
    dates = available_dates()
    await state.set_state(Booking.choosing_date)
    await call.message.edit_text(
        f"Мастер: <b>{master['name']}</b> ({master['specialization']})\n\nВыберите дату:",
        reply_markup=kb.dates_kb(dates),
    )
    await call.answer()


@router.callback_query(F.data == "back_to_masters", Booking.choosing_date)
async def cb_back_to_masters(call: CallbackQuery, state: FSMContext):
    masters = await db.get_masters()
    await state.set_state(Booking.choosing_master)
    await call.message.edit_text("Выберите мастера:", reply_markup=kb.masters_kb(masters))
    await call.answer()


@router.callback_query(F.data.startswith("date:"), Booking.choosing_date)
async def cb_choose_date(call: CallbackQuery, state: FSMContext):
    date_str = call.data.split(":", 1)[1]
    date = dt.date.fromisoformat(date_str)
    data = await state.get_data()
    master = await db.get_master(data["master_id"])
    service = await db.get_service(data["service_id"])
    busy = await db.get_busy_intervals(master["id"], date_str)
    slots = generate_time_slots(master, date, service["duration_minutes"], busy)

    await state.update_data(date=date_str)
    await state.set_state(Booking.choosing_time)

    if not slots:
        text = (
            f"На {format_date_human(date)} свободных окошек у мастера {master['name']} нет 😔\n"
            "Выберите другую дату:"
        )
        await call.message.edit_text(text, reply_markup=kb.dates_kb(available_dates()))
        await state.set_state(Booking.choosing_date)
    else:
        await call.message.edit_text(
            f"Дата: {format_date_human(date)}\nВыберите удобное время:",
            reply_markup=kb.times_kb(slots),
        )
    await call.answer()


@router.callback_query(F.data == "back_to_dates", Booking.choosing_time)
async def cb_back_to_dates(call: CallbackQuery, state: FSMContext):
    await state.set_state(Booking.choosing_date)
    await call.message.edit_text("Выберите дату:", reply_markup=kb.dates_kb(available_dates()))
    await call.answer()


@router.callback_query(F.data.startswith("time:"), Booking.choosing_time)
async def cb_choose_time(call: CallbackQuery, state: FSMContext):
    time_str = call.data.split(":", 1)[1]
    await state.update_data(time=time_str)

    client = await db.get_client(call.from_user.id)
    if client and client.get("name") and client.get("phone"):
        await state.update_data(client_name=client["name"], client_phone=client["phone"])
        await show_confirmation(call.message, state)
    else:
        await state.set_state(Booking.entering_name)
        await call.message.edit_text("Как вас зовут? Напишите имя для записи:")
    await call.answer()


@router.message(Booking.entering_name)
async def msg_entering_name(message: Message, state: FSMContext):
    name = message.text.strip()
    if len(name) < 2:
        await message.answer("Пожалуйста, введите корректное имя.")
        return
    await state.update_data(client_name=name)
    await state.set_state(Booking.entering_phone)
    await message.answer(
        "Отправьте номер телефона для подтверждения записи (кнопкой ниже или текстом):",
        reply_markup=kb.phone_request_kb(),
    )


@router.message(Booking.entering_phone, F.contact)
async def msg_entering_phone_contact(message: Message, state: FSMContext):
    phone = message.contact.phone_number
    await state.update_data(client_phone=phone)
    await message.answer("Спасибо!", reply_markup=kb.remove_kb())
    await show_confirmation(message, state)


@router.message(Booking.entering_phone, F.text)
async def msg_entering_phone_text(message: Message, state: FSMContext):
    phone = message.text.strip()
    if len(phone) < 5:
        await message.answer("Пожалуйста, введите корректный номер телефона.")
        return
    await state.update_data(client_phone=phone)
    await message.answer("Спасибо!", reply_markup=kb.remove_kb())
    await show_confirmation(message, state)


async def show_confirmation(message: Message, state: FSMContext):
    data = await state.get_data()
    service = await db.get_service(data["service_id"])
    master = await db.get_master(data["master_id"])
    date = dt.date.fromisoformat(data["date"])

    text = (
        "Проверьте данные записи:\n\n"
        f"💅 Услуга: <b>{service['name']}</b>\n"
        f"👩 Мастер: <b>{master['name']}</b>\n"
        f"📅 Дата: <b>{format_date_human(date)}</b>\n"
        f"🕐 Время: <b>{data['time']}</b>\n"
        f"💰 Стоимость: {format_price(service['price'])}\n"
        f"👤 Имя: {data['client_name']}\n"
        f"📞 Телефон: {data['client_phone']}\n\n"
        "Всё верно?"
    )
    await state.set_state(Booking.confirming)
    await message.answer(text, reply_markup=kb.confirm_booking_kb())


@router.callback_query(F.data == "cancel_booking", Booking.confirming)
async def cb_cancel_booking_flow(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await call.message.edit_text("Запись отменена. Возвращаемся в меню.")
    await show_main_menu(call.message, greet=False)
    await call.answer()


@router.callback_query(F.data == "confirm_booking", Booking.confirming)
async def cb_confirm_booking(call: CallbackQuery, state: FSMContext, bot: Bot):
    data = await state.get_data()
    await db.upsert_client(call.from_user.id, name=data["client_name"], phone=data["client_phone"])

    # повторная проверка, что слот всё ещё свободен (защита от гонки)
    master = await db.get_master(data["master_id"])
    service = await db.get_service(data["service_id"])
    busy = await db.get_busy_intervals(master["id"], data["date"])
    date_obj = dt.date.fromisoformat(data["date"])
    free_slots = generate_time_slots(master, date_obj, service["duration_minutes"], busy)
    if data["time"] not in free_slots:
        await call.message.edit_text(
            "К сожалению, это время только что заняли. Пожалуйста, выберите другое время через /menu."
        )
        await state.clear()
        await call.answer()
        return

    appointment_id = await db.create_appointment(
        client_id=call.from_user.id,
        client_name=data["client_name"],
        client_phone=data["client_phone"],
        service_id=data["service_id"],
        master_id=data["master_id"],
        date=data["date"],
        time=data["time"],
    )
    await state.clear()

    await call.message.edit_text(
        "✅ Запись подтверждена! Ждём вас в салоне.\n"
        "Напоминание придёт за 24 часа и за 2 часа до визита.\n\n"
        "Управлять записью можно в разделе «Мои записи»."
    )
    await show_main_menu(call.message, greet=False)
    await call.answer()

    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(
                admin_id,
                f"🆕 Новая запись #{appointment_id}\n"
                f"{data['client_name']} ({data['client_phone']})\n"
                f"{service['name']} у мастера {master['name']}\n"
                f"{format_date_human(date_obj)} в {data['time']}",
            )
        except Exception:
            logger.exception("Не удалось уведомить админа %s", admin_id)


# ---------------- Мои записи ----------------

@router.callback_query(F.data == "my_appointments")
async def cb_my_appointments(call: CallbackQuery, state: FSMContext):
    await state.clear()
    appts = await db.get_client_appointments(call.from_user.id, upcoming=True)
    if not appts:
        text = "У вас пока нет предстоящих записей."
        back = kb.InlineKeyboardBuilder()
        back.button(text="💅 Записаться", callback_data="book")
        back.button(text="⬅️ В меню", callback_data="back_to_menu")
        back.adjust(1)
        await call.message.edit_text(text, reply_markup=back.as_markup())
        await call.answer()
        return

    await call.message.edit_text(f"Ваши предстоящие записи ({len(appts)}):")
    for a in appts:
        date_obj = dt.date.fromisoformat(a["date"])
        text = (
            f"#{a['id']} · {format_date_human(date_obj)} в {a['time']}\n"
            f"{a['service_name']} — {a['master_name']}\n"
            f"{format_price(a['price'])}"
        )
        await call.message.answer(text, reply_markup=kb.appointment_actions_kb(a["id"]))
    await call.message.answer("Выберите действие:", reply_markup=kb.main_menu_kb())
    await call.answer()


@router.callback_query(F.data.startswith("cancel_appt:"))
async def cb_cancel_appt_confirm(call: CallbackQuery):
    appointment_id = int(call.data.split(":", 1)[1])
    await call.message.edit_text(
        "Точно отменить эту запись?",
        reply_markup=kb.confirm_cancel_kb(appointment_id),
    )
    await call.answer()


@router.callback_query(F.data.startswith("cancel_yes:"))
async def cb_cancel_appt_yes(call: CallbackQuery, bot: Bot):
    appointment_id = int(call.data.split(":", 1)[1])
    appt = await db.get_appointment(appointment_id)
    await db.cancel_appointment(appointment_id)
    await call.message.edit_text("Запись отменена.")
    await call.answer()

    if appt:
        for admin_id in ADMIN_IDS:
            try:
                await bot.send_message(
                    admin_id,
                    f"🚫 Отменена запись #{appointment_id}: {appt['client_name']} "
                    f"({appt['service_name']}, {appt['date']} {appt['time']})",
                )
            except Exception:
                logger.exception("Не удалось уведомить админа")


@router.callback_query(F.data == "cancel_no")
async def cb_cancel_appt_no(call: CallbackQuery):
    await call.message.edit_text("Хорошо, запись сохранена.")
    await call.answer()


# ---------------- Перенос записи ----------------

@router.callback_query(F.data.startswith("reschedule:"))
async def cb_reschedule_start(call: CallbackQuery, state: FSMContext):
    appointment_id = int(call.data.split(":", 1)[1])
    await state.update_data(reschedule_id=appointment_id)
    await state.set_state(Rescheduling.choosing_date)
    await call.message.edit_text("Выберите новую дату:", reply_markup=kb.dates_kb(available_dates(), back_callback="back_to_menu"))
    await call.answer()


@router.callback_query(F.data.startswith("date:"), Rescheduling.choosing_date)
async def cb_reschedule_date(call: CallbackQuery, state: FSMContext):
    date_str = call.data.split(":", 1)[1]
    date = dt.date.fromisoformat(date_str)
    data = await state.get_data()
    appt = await db.get_appointment(data["reschedule_id"])
    master = await db.get_master(appt["master_id"])
    busy = await db.get_busy_intervals(master["id"], date_str)
    slots = generate_time_slots(master, date, appt["duration"], busy)

    await state.update_data(new_date=date_str)
    if not slots:
        await call.message.edit_text(
            f"На {format_date_human(date)} свободных окошек нет. Выберите другую дату:",
            reply_markup=kb.dates_kb(available_dates(), back_callback="back_to_menu"),
        )
    else:
        await state.set_state(Rescheduling.choosing_time)
        await call.message.edit_text(
            f"Новая дата: {format_date_human(date)}\nВыберите время:",
            reply_markup=kb.times_kb(slots, back_callback="back_to_menu"),
        )
    await call.answer()


@router.callback_query(F.data.startswith("time:"), Rescheduling.choosing_time)
async def cb_reschedule_time(call: CallbackQuery, state: FSMContext, bot: Bot):
    time_str = call.data.split(":", 1)[1]
    data = await state.get_data()
    appointment_id = data["reschedule_id"]
    appt = await db.get_appointment(appointment_id)

    await db.reschedule_appointment(appointment_id, data["new_date"], time_str)
    await state.clear()

    date_obj = dt.date.fromisoformat(data["new_date"])
    await call.message.edit_text(
        f"✅ Запись перенесена на {format_date_human(date_obj)} в {time_str}."
    )
    await show_main_menu(call.message, greet=False)
    await call.answer()

    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(
                admin_id,
                f"🔁 Перенесена запись #{appointment_id}: {appt['client_name']} → "
                f"{data['new_date']} {time_str}",
            )
        except Exception:
            logger.exception("Не удалось уведомить админа")


# ---------------- История визитов ----------------

@router.callback_query(F.data == "history")
async def cb_history(call: CallbackQuery, state: FSMContext):
    await state.clear()
    appts = await db.get_client_appointments(call.from_user.id, upcoming=False)
    if not appts:
        text = "История визитов пока пуста."
    else:
        lines = [f"🕓 История визитов ({len(appts)}):\n"]
        for a in appts[:15]:
            date_obj = dt.date.fromisoformat(a["date"])
            status_icon = "✅" if a["status"] == "completed" else "❌" if a["status"] == "cancelled" else "•"
            lines.append(
                f"{status_icon} {format_date_human(date_obj)} — {a['service_name']} у {a['master_name']}"
            )
        text = "\n".join(lines)
    back = kb.InlineKeyboardBuilder()
    back.button(text="⬅️ В меню", callback_data="back_to_menu")
    await call.message.edit_text(text, reply_markup=back.as_markup())
    await call.answer()
