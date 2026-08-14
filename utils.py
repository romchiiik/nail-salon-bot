"""Вспомогательные функции: генерация слотов, форматирование дат."""
import datetime as dt

from config import SLOT_STEP_MINUTES, DAYS_AHEAD_FOR_BOOKING

WEEKDAYS_RU = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
MONTHS_RU = [
    "", "января", "февраля", "марта", "апреля", "мая", "июня",
    "июля", "августа", "сентября", "октября", "ноября", "декабря",
]


def available_dates():
    """Список доступных для записи дат (учитывая DAYS_AHEAD_FOR_BOOKING вперёд)."""
    today = dt.date.today()
    return [today + dt.timedelta(days=i) for i in range(DAYS_AHEAD_FOR_BOOKING)]


def format_date_human(date: dt.date) -> str:
    return f"{date.day} {MONTHS_RU[date.month]} ({WEEKDAYS_RU[date.weekday()]})"


def is_day_off(master: dict, date: dt.date) -> bool:
    days_off = master.get("days_off") or ""
    off_days = {int(x) for x in days_off.split(",") if x.strip().isdigit()}
    return date.weekday() in off_days


def generate_time_slots(master: dict, date: dt.date, duration_minutes: int, busy_intervals):
    """
    Возвращает список свободных 'HH:MM' слотов для мастера на дату с учётом
    длительности услуги и уже забронированных интервалов.
    """
    if is_day_off(master, date):
        return []

    work_start = master.get("work_start", 10) * 60
    work_end = master.get("work_end", 20) * 60

    now = dt.datetime.now()
    is_today = date == now.date()
    min_start = now.hour * 60 + now.minute + 30 if is_today else 0  # минимум +30 минут от текущего времени

    slots = []
    t = work_start
    while t + duration_minutes <= work_end:
        if not is_today or t >= min_start:
            overlap = any(t < b_end and (t + duration_minutes) > b_start for b_start, b_end in busy_intervals)
            if not overlap:
                h, m = divmod(t, 60)
                slots.append(f"{h:02d}:{m:02d}")
        t += SLOT_STEP_MINUTES
    return slots


def format_price(price: int) -> str:
    return f"{price} ₽"


def format_duration(minutes: int) -> str:
    h, m = divmod(minutes, 60)
    if h and m:
        return f"{h} ч {m} мин"
    if h:
        return f"{h} ч"
    return f"{m} мин"
