"""
Слой работы с базой данных (SQLite, асинхронно через aiosqlite).
Хранит клиентов, услуги, мастеров, записи и отзывы.
"""
import datetime as dt
import aiosqlite

from config import DB_PATH, WORK_START_HOUR, WORK_END_HOUR

SCHEMA = """
CREATE TABLE IF NOT EXISTS clients (
    telegram_id INTEGER PRIMARY KEY,
    name TEXT,
    phone TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS services (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    category TEXT NOT NULL,
    price INTEGER NOT NULL,
    duration_minutes INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS masters (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    specialization TEXT,
    work_start INTEGER DEFAULT 10,
    work_end INTEGER DEFAULT 20,
    days_off TEXT DEFAULT ''   -- через запятую: '0,6' = пн и вс выходной
);

CREATE TABLE IF NOT EXISTS appointments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id INTEGER NOT NULL,
    client_name TEXT,
    client_phone TEXT,
    service_id INTEGER NOT NULL,
    master_id INTEGER NOT NULL,
    date TEXT NOT NULL,        -- YYYY-MM-DD
    time TEXT NOT NULL,        -- HH:MM
    status TEXT DEFAULT 'confirmed',  -- confirmed / cancelled / completed
    created_at TEXT DEFAULT (datetime('now')),
    reminded_24h INTEGER DEFAULT 0,
    reminded_2h INTEGER DEFAULT 0,
    asked_review INTEGER DEFAULT 0,
    FOREIGN KEY (service_id) REFERENCES services (id),
    FOREIGN KEY (master_id) REFERENCES masters (id)
);

CREATE TABLE IF NOT EXISTS reviews (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    appointment_id INTEGER NOT NULL,
    client_id INTEGER NOT NULL,
    rating INTEGER NOT NULL,
    comment TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (appointment_id) REFERENCES appointments (id)
);
"""

DEFAULT_SERVICES = [
    # name, category, price, duration_minutes
    ("Маникюр классический", "Маникюр", 1500, 60),
    ("Маникюр аппаратный", "Маникюр", 1800, 60),
    ("Покрытие гель-лак", "Маникюр", 2200, 90),
    ("Наращивание ногтей", "Маникюр", 3500, 150),
    ("Дизайн (1 ноготь)", "Дизайн", 150, 15),
    ("Педикюр классический", "Педикюр", 2000, 75),
    ("Педикюр аппаратный", "Педикюр", 2500, 90),
    ("Снятие покрытия", "Другое", 500, 30),
]

DEFAULT_MASTERS = [
    # name, specialization, work_start, work_end, days_off
    ("Анна", "Маникюр, дизайн ногтей", 10, 20, "0"),      # выходной пн
    ("Мария", "Педикюр, наращивание", 10, 20, "6"),        # выходной вс
    ("Ольга", "Маникюр, педикюр", 11, 19, "0,6"),           # выходной пн, вс
]


async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript(SCHEMA)
        await db.commit()

        cur = await db.execute("SELECT COUNT(*) FROM services")
        (count,) = await cur.fetchone()
        if count == 0:
            await db.executemany(
                "INSERT INTO services (name, category, price, duration_minutes) VALUES (?, ?, ?, ?)",
                DEFAULT_SERVICES,
            )
        cur = await db.execute("SELECT COUNT(*) FROM masters")
        (count,) = await cur.fetchone()
        if count == 0:
            await db.executemany(
                "INSERT INTO masters (name, specialization, work_start, work_end, days_off) VALUES (?, ?, ?, ?, ?)",
                DEFAULT_MASTERS,
            )
        await db.commit()


# ---------- Клиенты ----------

async def upsert_client(telegram_id: int, name: str = None, phone: str = None):
    async with aiosqlite.connect(DB_PATH) as db:
        existing = await (await db.execute(
            "SELECT telegram_id FROM clients WHERE telegram_id = ?", (telegram_id,)
        )).fetchone()
        if existing:
            if name:
                await db.execute("UPDATE clients SET name = ? WHERE telegram_id = ?", (name, telegram_id))
            if phone:
                await db.execute("UPDATE clients SET phone = ? WHERE telegram_id = ?", (phone, telegram_id))
        else:
            await db.execute(
                "INSERT INTO clients (telegram_id, name, phone) VALUES (?, ?, ?)",
                (telegram_id, name, phone),
            )
        await db.commit()


async def get_client(telegram_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        row = await (await db.execute(
            "SELECT * FROM clients WHERE telegram_id = ?", (telegram_id,)
        )).fetchone()
        return dict(row) if row else None


async def get_all_client_ids():
    async with aiosqlite.connect(DB_PATH) as db:
        rows = await (await db.execute("SELECT telegram_id FROM clients")).fetchall()
        return [r[0] for r in rows]


# ---------- Услуги и мастера ----------

async def get_services():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        rows = await (await db.execute("SELECT * FROM services ORDER BY category, id")).fetchall()
        return [dict(r) for r in rows]


async def get_service(service_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        row = await (await db.execute("SELECT * FROM services WHERE id = ?", (service_id,))).fetchone()
        return dict(row) if row else None


async def get_masters():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        rows = await (await db.execute("SELECT * FROM masters ORDER BY id")).fetchall()
        return [dict(r) for r in rows]


async def get_master(master_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        row = await (await db.execute("SELECT * FROM masters WHERE id = ?", (master_id,))).fetchone()
        return dict(row) if row else None


# ---------- Записи ----------

async def get_busy_intervals(master_id: int, date: str):
    """Возвращает список (start_minutes, end_minutes) занятых интервалов мастера на дату."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        rows = await (await db.execute(
            """
            SELECT a.time AS time, s.duration_minutes AS duration
            FROM appointments a
            JOIN services s ON s.id = a.service_id
            WHERE a.master_id = ? AND a.date = ? AND a.status = 'confirmed'
            """,
            (master_id, date),
        )).fetchall()
    intervals = []
    for r in rows:
        h, m = map(int, r["time"].split(":"))
        start = h * 60 + m
        end = start + r["duration"]
        intervals.append((start, end))
    return intervals


async def create_appointment(client_id, client_name, client_phone, service_id, master_id, date, time):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            """
            INSERT INTO appointments (client_id, client_name, client_phone, service_id, master_id, date, time)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (client_id, client_name, client_phone, service_id, master_id, date, time),
        )
        await db.commit()
        return cur.lastrowid


async def get_appointment(appointment_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        row = await (await db.execute(
            """
            SELECT a.*, s.name AS service_name, s.price AS price, s.duration_minutes AS duration,
                   m.name AS master_name
            FROM appointments a
            JOIN services s ON s.id = a.service_id
            JOIN masters m ON m.id = a.master_id
            WHERE a.id = ?
            """,
            (appointment_id,),
        )).fetchone()
        return dict(row) if row else None


async def get_client_appointments(client_id: int, upcoming: bool = True):
    today = dt.date.today().isoformat()
    now_time = dt.datetime.now().strftime("%H:%M")
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        if upcoming:
            rows = await (await db.execute(
                """
                SELECT a.*, s.name AS service_name, s.price AS price, s.duration_minutes AS duration,
                       m.name AS master_name
                FROM appointments a
                JOIN services s ON s.id = a.service_id
                JOIN masters m ON m.id = a.master_id
                WHERE a.client_id = ? AND a.status = 'confirmed'
                  AND (a.date > ? OR (a.date = ? AND a.time >= ?))
                ORDER BY a.date, a.time
                """,
                (client_id, today, today, now_time),
            )).fetchall()
        else:
            rows = await (await db.execute(
                """
                SELECT a.*, s.name AS service_name, s.price AS price, s.duration_minutes AS duration,
                       m.name AS master_name
                FROM appointments a
                JOIN services s ON s.id = a.service_id
                JOIN masters m ON m.id = a.master_id
                WHERE a.client_id = ?
                  AND (a.status = 'completed' OR a.date < ? OR (a.date = ? AND a.time < ?))
                  AND a.status != 'cancelled'
                ORDER BY a.date DESC, a.time DESC
                """,
                (client_id, today, today, now_time),
            )).fetchall()
        return [dict(r) for r in rows]


async def cancel_appointment(appointment_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE appointments SET status = 'cancelled' WHERE id = ?", (appointment_id,))
        await db.commit()


async def reschedule_appointment(appointment_id: int, new_date: str, new_time: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE appointments SET date = ?, time = ?, reminded_24h = 0, reminded_2h = 0 WHERE id = ?",
            (new_date, new_time, appointment_id),
        )
        await db.commit()


# ---------- Админ ----------

async def get_appointments_for_date(date: str):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        rows = await (await db.execute(
            """
            SELECT a.*, s.name AS service_name, m.name AS master_name
            FROM appointments a
            JOIN services s ON s.id = a.service_id
            JOIN masters m ON m.id = a.master_id
            WHERE a.date = ? AND a.status = 'confirmed'
            ORDER BY a.time
            """,
            (date,),
        )).fetchall()
        return [dict(r) for r in rows]


async def get_upcoming_appointments(limit: int = 50):
    today = dt.date.today().isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        rows = await (await db.execute(
            """
            SELECT a.*, s.name AS service_name, m.name AS master_name
            FROM appointments a
            JOIN services s ON s.id = a.service_id
            JOIN masters m ON m.id = a.master_id
            WHERE a.date >= ? AND a.status = 'confirmed'
            ORDER BY a.date, a.time
            LIMIT ?
            """,
            (today, limit),
        )).fetchall()
        return [dict(r) for r in rows]


async def get_stats():
    async with aiosqlite.connect(DB_PATH) as db:
        clients = (await (await db.execute("SELECT COUNT(*) FROM clients")).fetchone())[0]
        total_appts = (await (await db.execute("SELECT COUNT(*) FROM appointments WHERE status != 'cancelled'")).fetchone())[0]
        cancelled = (await (await db.execute("SELECT COUNT(*) FROM appointments WHERE status = 'cancelled'")).fetchone())[0]
        month = dt.date.today().strftime("%Y-%m")
        revenue_row = await (await db.execute(
            """
            SELECT COALESCE(SUM(s.price), 0) FROM appointments a
            JOIN services s ON s.id = a.service_id
            WHERE a.status != 'cancelled' AND substr(a.date, 1, 7) = ?
            """,
            (month,),
        )).fetchone()
        avg_rating_row = await (await db.execute("SELECT AVG(rating) FROM reviews")).fetchone()
        return {
            "clients": clients,
            "total_appointments": total_appts,
            "cancelled": cancelled,
            "month_revenue": revenue_row[0],
            "avg_rating": round(avg_rating_row[0], 2) if avg_rating_row[0] else None,
        }


# ---------- Напоминания и отзывы ----------

async def get_appointments_needing_24h_reminder():
    target_dt = dt.datetime.now() + dt.timedelta(hours=24)
    window_start = target_dt - dt.timedelta(minutes=30)
    window_end = target_dt + dt.timedelta(minutes=30)
    return await _appointments_in_window(window_start, window_end, "reminded_24h")


async def get_appointments_needing_2h_reminder():
    target_dt = dt.datetime.now() + dt.timedelta(hours=2)
    window_start = target_dt - dt.timedelta(minutes=15)
    window_end = target_dt + dt.timedelta(minutes=15)
    return await _appointments_in_window(window_start, window_end, "reminded_2h")


async def _appointments_in_window(window_start, window_end, flag_field):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        rows = await (await db.execute(
            f"""
            SELECT a.*, s.name AS service_name, m.name AS master_name
            FROM appointments a
            JOIN services s ON s.id = a.service_id
            JOIN masters m ON m.id = a.master_id
            WHERE a.status = 'confirmed' AND a.{flag_field} = 0
            """
        )).fetchall()
    result = []
    for r in rows:
        row = dict(r)
        appt_dt = dt.datetime.strptime(f"{row['date']} {row['time']}", "%Y-%m-%d %H:%M")
        if window_start <= appt_dt <= window_end:
            result.append(row)
    return result


async def mark_reminded(appointment_id: int, field: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(f"UPDATE appointments SET {field} = 1 WHERE id = ?", (appointment_id,))
        await db.commit()


async def get_appointments_needing_review_request():
    """Записи, которые уже завершились (дата+время в прошлом) и по которым ещё не спрашивали отзыв."""
    now = dt.datetime.now()
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        rows = await (await db.execute(
            """
            SELECT a.*, s.name AS service_name, m.name AS master_name, s.duration_minutes AS duration
            FROM appointments a
            JOIN services s ON s.id = a.service_id
            JOIN masters m ON m.id = a.master_id
            WHERE a.status = 'confirmed' AND a.asked_review = 0
            """
        )).fetchall()
    result = []
    for r in rows:
        row = dict(r)
        start_dt = dt.datetime.strptime(f"{row['date']} {row['time']}", "%Y-%m-%d %H:%M")
        end_dt = start_dt + dt.timedelta(minutes=row["duration"])
        if now >= end_dt:
            result.append(row)
    return result


async def mark_asked_review(appointment_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE appointments SET asked_review = 1, status = 'completed' WHERE id = ?", (appointment_id,))
        await db.commit()


async def add_review(appointment_id: int, client_id: int, rating: int, comment: str = None):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO reviews (appointment_id, client_id, rating, comment) VALUES (?, ?, ?, ?)",
            (appointment_id, client_id, rating, comment),
        )
        await db.commit()


async def get_recent_reviews(limit: int = 10):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        rows = await (await db.execute(
            """
            SELECT r.*, a.date, a.time, s.name AS service_name
            FROM reviews r
            JOIN appointments a ON a.id = r.appointment_id
            JOIN services s ON s.id = a.service_id
            ORDER BY r.created_at DESC
            LIMIT ?
            """,
            (limit,),
        )).fetchall()
        return [dict(r) for r in rows]
