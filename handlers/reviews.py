"""Хендлеры для сбора отзывов после визита."""
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext

import database as db
import keyboards as kb
from states import Review

router = Router()


@router.callback_query(F.data.startswith("rate:"))
async def cb_rate(call: CallbackQuery, state: FSMContext):
    _, appointment_id, rating = call.data.split(":")
    await state.update_data(review_appointment_id=int(appointment_id), review_rating=int(rating))
    await state.set_state(Review.entering_comment)
    await call.message.edit_text(
        f"Спасибо за оценку {'⭐' * int(rating)}!\n"
        "Хотите оставить комментарий? Напишите его сообщением или нажмите «Пропустить»."
    , reply_markup=kb.skip_comment_kb())
    await call.answer()


@router.message(Review.entering_comment)
async def msg_review_comment(message: Message, state: FSMContext):
    data = await state.get_data()
    await db.add_review(
        appointment_id=data["review_appointment_id"],
        client_id=message.from_user.id,
        rating=data["review_rating"],
        comment=message.text,
    )
    await state.clear()
    await message.answer("Спасибо, ваш отзыв сохранён! 💖")


@router.callback_query(F.data == "skip_comment", Review.entering_comment)
async def cb_skip_comment(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    await db.add_review(
        appointment_id=data["review_appointment_id"],
        client_id=call.from_user.id,
        rating=data["review_rating"],
        comment=None,
    )
    await state.clear()
    await call.message.edit_text("Спасибо за оценку! 💖")
    await call.answer()
