from aiogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardRemove,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder

from utils import format_date_human, format_price, format_duration

MAIN_MENU_BOOK = "book"
MAIN_MENU_MY = "my_appointments"
MAIN_MENU_HISTORY = "history"
MAIN_MENU_CONTACTS = "contacts"


def main_menu_kb():
    kb = InlineKeyboardBuilder()
    kb.button(text="💅 Записаться", callback_data=MAIN_MENU_BOOK)
    kb.button(text="📅 Мои записи", callback_data=MAIN_MENU_MY)
    kb.button(text="🕓 История визитов", callback_data=MAIN_MENU_HISTORY)
    kb.button(text="ℹ️ Контакты и адрес", callback_data=MAIN_MENU_CONTACTS)
    kb.adjust(1)
    return kb.as_markup()


def categories_kb(categories):
    kb = InlineKeyboardBuilder()
    for cat in categories:
        kb.button(text=cat, callback_data=f"cat:{cat}")
    kb.button(text="⬅️ Назад", callback_data="back_to_menu")
    kb.adjust(1)
    return kb.as_markup()


def services_kb(services):
    kb = InlineKeyboardBuilder()
    for s in services:
        label = f"{s['name']} — {format_price(s['price'])} ({format_duration(s['duration_minutes'])})"
        kb.button(text=label, callback_data=f"service:{s['id']}")
    kb.button(text="⬅️ Назад", callback_data="back_to_categories")
    kb.adjust(1)
    return kb.as_markup()


def masters_kb(masters):
    kb = InlineKeyboardBuilder()
    for m in masters:
        kb.button(text=f"{m['name']} — {m['specialization']}", callback_data=f"master:{m['id']}")
    kb.button(text="⬅️ Назад", callback_data="back_to_services")
    kb.adjust(1)
    return kb.as_markup()


def dates_kb(dates, back_callback="back_to_masters"):
    kb = InlineKeyboardBuilder()
    for d in dates:
        kb.button(text=format_date_human(d), callback_data=f"date:{d.isoformat()}")
    kb.button(text="⬅️ Назад", callback_data=back_callback)
    kb.adjust(2)
    return kb.as_markup()


def times_kb(slots, back_callback="back_to_dates"):
    kb = InlineKeyboardBuilder()
    for t in slots:
        kb.button(text=t, callback_data=f"time:{t}")
    kb.button(text="⬅️ Назад", callback_data=back_callback)
    kb.adjust(4)
    return kb.as_markup()


def phone_request_kb():
    kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📱 Отправить номер телефона", request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )
    return kb


def remove_kb():
    return ReplyKeyboardRemove()


def confirm_booking_kb():
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Подтвердить запись", callback_data="confirm_booking")
    kb.button(text="❌ Отменить", callback_data="cancel_booking")
    kb.adjust(1)
    return kb.as_markup()


def appointment_actions_kb(appointment_id: int):
    kb = InlineKeyboardBuilder()
    kb.button(text="🔁 Перенести", callback_data=f"reschedule:{appointment_id}")
    kb.button(text="🚫 Отменить запись", callback_data=f"cancel_appt:{appointment_id}")
    kb.adjust(1)
    return kb.as_markup()


def confirm_cancel_kb(appointment_id: int):
    kb = InlineKeyboardBuilder()
    kb.button(text="Да, отменить", callback_data=f"cancel_yes:{appointment_id}")
    kb.button(text="Нет, оставить", callback_data="cancel_no")
    kb.adjust(1)
    return kb.as_markup()


def rating_kb(appointment_id: int):
    kb = InlineKeyboardBuilder()
    for i in range(1, 6):
        kb.button(text="⭐" * i, callback_data=f"rate:{appointment_id}:{i}")
    kb.adjust(1)
    return kb.as_markup()


def skip_comment_kb():
    kb = InlineKeyboardBuilder()
    kb.button(text="Пропустить", callback_data="skip_comment")
    kb.adjust(1)
    return kb.as_markup()


# ---------- Admin ----------

def admin_menu_kb():
    kb = InlineKeyboardBuilder()
    kb.button(text="📋 Записи на сегодня", callback_data="adm_today")
    kb.button(text="📆 Все ближайшие записи", callback_data="adm_upcoming")
    kb.button(text="📊 Статистика", callback_data="adm_stats")
    kb.button(text="⭐ Последние отзывы", callback_data="adm_reviews")
    kb.button(text="📢 Рассылка клиентам", callback_data="adm_broadcast")
    kb.adjust(1)
    return kb.as_markup()


def admin_broadcast_confirm_kb():
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Отправить всем", callback_data="adm_broadcast_send")
    kb.button(text="❌ Отмена", callback_data="adm_broadcast_cancel")
    kb.adjust(1)
    return kb.as_markup()


def back_to_admin_kb():
    kb = InlineKeyboardBuilder()
    kb.button(text="⬅️ В админ-меню", callback_data="adm_menu")
    kb.adjust(1)
    return kb.as_markup()
