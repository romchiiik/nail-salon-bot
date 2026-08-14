import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
ADMIN_IDS = [
    int(x.strip())
    for x in os.getenv("ADMIN_IDS", "").split(",")
    if x.strip().isdigit()
]

SALON_NAME = os.getenv("SALON_NAME", "Beauty Nails Studio")
DB_PATH = os.getenv("DB_PATH", "salon.db")

# Рабочие часы салона по умолчанию
WORK_START_HOUR = 10
WORK_END_HOUR = 20
SLOT_STEP_MINUTES = 30
DAYS_AHEAD_FOR_BOOKING = 14  # на сколько дней вперёд можно записаться

if not BOT_TOKEN:
    raise RuntimeError(
        "BOT_TOKEN не задан. Создайте файл .env на основе .env.example "
        "и укажите токен бота, полученный у @BotFather."
    )
