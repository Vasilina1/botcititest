from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.callback_data import CallbackData

from tgbot.services.service import DAYS


ID_SUPER_USERS = ()


def kb_start(clear: bool = False, free_days: bool = True) -> InlineKeyboardMarkup:
    """Клавиатура меню"""
    kb = InlineKeyboardMarkup(row_width=1)
    if free_days:
        kb.add(InlineKeyboardButton(text="Пожелания по графику", callback_data="start"))
    if clear:
        kb.insert(InlineKeyboardButton(text="Сбросить пожелания по графику", callback_data="clear"))
    kb.insert(InlineKeyboardButton(text="Просмотр записанных данных", callback_data="show"))
    return kb


callback_days = CallbackData("days", "day", "make")


def kb_days(days: list, selected_days: tuple = ()) -> InlineKeyboardMarkup:
    """Клавиатура выбора дней"""
    kb = InlineKeyboardMarkup(row_width=7)
    checkbox = {True: "✅", False: "☑"}
    makes = {True: "cancel", False: "select"}
    for day in days:
        kb.insert(
            InlineKeyboardButton(
                text=f"{checkbox[day in selected_days]} {day}",
                callback_data=callback_days.new(day=day, make=makes[day in selected_days])
            )
        )
    if selected_days:
        kb.add(InlineKeyboardButton(
            text=f"Продолжить с этими днями: {', '.join(selected_days)}",
            callback_data=callback_days.new(day="no", make="next")
        ))
    return kb


callback_data_intervals = CallbackData("intervals", "interval", "day")


def is_super(user_id: int):
    return user_id in ID_SUPER_USERS


def kb_intervals(intervals: dict, day: str, user_id: int, type_user: str) -> InlineKeyboardMarkup:
    """Клавиатура выбра интервалов"""
    kb = InlineKeyboardMarkup(row_width=3)
    intervals = intervals.copy()
    if not is_super(user_id) and type_user == "manager":
        del intervals["06:00-14:30(с)"]
        del intervals["14:30-23:00(с)"]
        del intervals["15:30-00:00(с)"]
    for interval in intervals:
        kb.insert(InlineKeyboardButton(
            text=interval,
            callback_data=callback_data_intervals.new(interval=interval.replace(':', "."), day=day)
        ))
    return kb
