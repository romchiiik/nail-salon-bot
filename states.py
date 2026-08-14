from aiogram.fsm.state import State, StatesGroup


class Booking(StatesGroup):
    choosing_category = State()
    choosing_service = State()
    choosing_master = State()
    choosing_date = State()
    choosing_time = State()
    entering_name = State()
    entering_phone = State()
    confirming = State()


class Rescheduling(StatesGroup):
    choosing_date = State()
    choosing_time = State()


class Review(StatesGroup):
    entering_comment = State()


class AdminBroadcast(StatesGroup):
    entering_text = State()
    confirming = State()


class AdminDayOff(StatesGroup):
    choosing_master = State()
    entering_date = State()
