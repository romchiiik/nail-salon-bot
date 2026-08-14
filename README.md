# 💅 Telegram-бот для маникюрного салона

Демо-проект для портфолио: Telegram-бот на **aiogram 3** с полным циклом записи —
выбор услуги/мастера/даты/времени, подтверждение, напоминания за 24ч и 2ч,
отмена и перенос записи, история визитов, сбор отзывов, и админ-панель для
владельца салона (записи на сегодня, статистика, рассылка клиентам).

Данные хранятся в SQLite (`salon.db`), создаётся автоматически при первом запуске.

## Возможности

- Запись клиента: категория → услуга → мастер → дата → время → имя/телефон → подтверждение
- Проверка занятости слотов в реальном времени (без двойных записей)
- «Мои записи»: отмена и перенос записи в 2 клика
- История визитов
- Автоматические напоминания за 24 часа и за 2 часа до визита
- Запрос отзыва (оценка звёздами + комментарий) после визита
- Админ-панель (`/admin`): записи на сегодня, ближайшие записи, статистика,
  последние отзывы, рассылка сообщения всем клиентам

## Структура проекта

```
nail_salon_bot/
├── bot.py              # точка входа
├── config.py            # переменные окружения
├── database.py           # работа с SQLite
├── keyboards.py          # inline-клавиатуры
├── states.py             # FSM-состояния
├── utils.py              # генерация слотов, форматирование
├── scheduler.py           # напоминания и запрос отзывов (APScheduler)
├── handlers/
│   ├── client.py          # запись, мои записи, история, отмена/перенос
│   ├── admin.py            # админ-панель
│   └── reviews.py          # сбор отзывов
├── requirements.txt
├── .env.example
└── Procfile               # для деплоя на Railway/Render
```

## Запуск локально (для разработки)

1. Установите зависимости:
   ```
   pip install -r requirements.txt
   ```
2. Скопируйте `.env.example` в `.env` и заполните:
   - `BOT_TOKEN` — получите у [@BotFather](https://t.me/BotFather) командой `/newbot`
   - `ADMIN_IDS` — ваш Telegram ID (узнать у [@userinfobot](https://t.me/userinfobot))
3. Запустите:
   ```
   python bot.py
   ```

Пока процесс работает — бот отвечает. Как только вы закроете терминал или
выключите ноутбук, бот остановится. Чтобы он работал **круглосуточно и
без вашего компьютера**, его нужно задеплоить на сервер — см. ниже.

## Деплой на 24/7 хостинг (чтобы бот работал без вашего Mac)

Boт — это процесс с постоянным подключением к Telegram (long polling),
поэтому подходит не любой "free" хостинг: важно, чтобы сервис не "засыпал"
между запросами. Ниже — рабочие варианты. Актуальные цены и лимиты
хостингов периодически меняются, стоит свериться с их сайтом перед оплатой.

### Вариант 1 — Render.com (рекомендуется, проще всего)

Render поддерживает тип сервиса **Background Worker**, который не "спит"
между сообщениями (в отличие от обычного Web Service) — то, что нужно для
long-polling бота.

1. Залейте папку `nail_salon_bot` в свой репозиторий на GitHub.
2. На [render.com](https://render.com) → **New** → **Background Worker**.
3. Подключите репозиторий.
4. Настройки сборки:
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `python bot.py`
5. В разделе Environment добавьте переменные из `.env.example`
   (`BOT_TOKEN`, `ADMIN_IDS`, `SALON_NAME`, `DB_PATH`).
6. Задеплойте. В логах должно появиться `Бот запущен, начинаем polling...`.

⚠️ На бесплатном плане диск эфемерный — при передеплое `salon.db` очистится.
Для портфолио это некритично; для реального салона добавьте Render Disk
(платно, от ~$1/мес) или переключитесь на внешнюю БД (Postgres).

### Вариант 2 — Railway.app

1. [railway.app](https://railway.app) → **New Project** → **Deploy from GitHub repo**.
2. Railway сам подхватит `Procfile` (`worker: python bot.py`).
3. Добавьте переменные окружения в Settings → Variables.
4. Новым аккаунтам даётся стартовый бесплатный кредит; дальше — оплата по
   факту использования (обычно доли доллара в месяц для такого лёгкого бота).
5. Чтобы данные (`salon.db`) не терялись при редеплое — подключите Railway Volume.

### Вариант 3 — Свой VPS / Oracle Cloud Free Tier

Самый надёжный вариант для постоянной работы — обычный сервер (в т.ч. есть
бессрочно бесплатные ARM-инстансы у Oracle Cloud Always Free).

```bash
git clone <ваш-репозиторий>
cd nail_salon_bot
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # заполните токен
# запуск как systemd-сервис, чтобы бот поднимался сам после перезагрузки
```

Пример `systemd`-юнита (`/etc/systemd/system/nailbot.service`):
```ini
[Unit]
Description=Nail Salon Telegram Bot
After=network.target

[Service]
WorkingDirectory=/home/user/nail_salon_bot
ExecStart=/home/user/nail_salon_bot/venv/bin/python bot.py
Restart=always
EnvironmentFile=/home/user/nail_salon_bot/.env

[Install]
WantedBy=multi-user.target
```
```bash
sudo systemctl enable --now nailbot
```

## Как показать в портфолио

- Прикрепите ссылку на живого бота в Telegram (например `t.me/your_salon_bot`)
- Дайте ссылку на репозиторий с кодом
- Запишите короткое демо-видео/GIF всего цикла записи

## Технологии

Python 3.10+, aiogram 3, aiosqlite, APScheduler, SQLite.
