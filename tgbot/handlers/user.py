import logging

from gspread_asyncio import AsyncioGspreadClient
from aiogram import Dispatcher
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup
from aiogram.dispatcher.storage import FSMContext

from tgbot.keyboards import kb_inline
from tgbot.services.google_sheets.google_sheets import get_worksheet
from tgbot.services import service

MANAGERS = {784125463:	"Зварич"}
DISPATCHERS = {740148238: "Смирнова"}


def get_type_user(user_id: int) -> str:
    """Определение типа пользователя"""
    if user_id in MANAGERS:
        return "manager"
    return "dispatcher"


def get_names(user_id: int) -> str:
    """Возвращает имя пользователя"""
    if user_id in MANAGERS:
        return MANAGERS.get(user_id)
    return DISPATCHERS.get(user_id)


async def check_records_in_table(client: AsyncioGspreadClient, user_id: int) -> tuple[str, InlineKeyboardMarkup]:
    """Формирует текст начального сообщения и клавиатуру в зависимости от того, есть ли записи в таблице"""
    worksheet = await get_worksheet(client)
    user_records = True if await service.get_all_cell_by_name(worksheet, get_names(user_id)) else False
    logging.info(f"{user_id} - {get_names(user_id)}")
    kb = kb_inline.kb_start(user_records)
    text = 'Нажмите "Пожелания по графику", чтобы отметить смены'
    if user_records:
        text += '\nНажмите "Сбросить пожелания по графику", чтобы сбросить все пожелания'
    return text, kb


async def get_free_days(client_manager, name, type_user) -> list:
    """Возвращает список дней, в которые не записан пользователь. Если свободно меньше 3 дней, возвращает None"""
    client = await client_manager.authorize()
    worksheet = await get_worksheet(client)
    days = await service.get_free_days(worksheet, name, type_user)
    return days


# handler
async def handler_cmd_start(msg: Message, state: FSMContext):
    """Хендлер команды старт. Отправляет сообщение и клавиатуру с началом выбора смен и опционально сбросом смен"""
    if not get_names(msg.from_user.id):
        await msg.answer("Вы не добавлены в бота. Обратитесь к @zvarich")
        return
    client_manager = msg.bot.get("google_client_manager")
    client = await client_manager.authorize()
    text, kb = await check_records_in_table(client, msg.from_user.id)
    await msg.answer(text=text, reply_markup=kb)
    await state.finish()


async def show_my_preferences(call: CallbackQuery):
    """Хендрел на кнопку Просмотр записанных данных. Выводит список смен пользователя из таблицы"""
    await call.answer()
    client_manager = call.bot.get("google_client_manager")
    shifts = await service.get_user_shifts(
        google_manager=client_manager,
        username=get_names(call.from_user.id),
        type_user=get_type_user(call.from_user.id)
    )
    if not shifts:
        await call.message.edit_text("Вы никуда не записаны")
    text = "Мои смены:"
    for day, shift in shifts.items():
        text += f"\n{day.capitalize()}. - {shift}"
    await call.message.edit_text(text)


# handler
async def handler_clear_preferences(call: CallbackQuery):
    """Хендлер реагирует на кнопку очистки пожеланий из таблицы"""
    await call.answer()
    client_manager = call.bot.get("google_client_manager")
    client = await client_manager.authorize()
    if not service.time_in_range():
        await call.message.edit_text("Извините, время сбора пожеланий закончилось")
        text, kb = await check_records_in_table(client, call.from_user.id)
        await call.message.answer(text, reply_markup=kb)
        return
    name = get_names(call.from_user.id)
    await service.clear_preferences(client, name)
    await call.message.answer("Готово")


# handler
async def handler_select_preferences(call: CallbackQuery, state: FSMContext):
    """Хендлер на кнопку """
    await call.answer()
    if not service.time_in_range():
        await call.message.edit_text("Извините, время сбора пожеланий закончилось")
        client_manager = call.bot.get("google_client_manager")
        client = await client_manager.authorize()
        text, kb = await check_records_in_table(client, call.from_user.id)
        await call.message.answer(text, reply_markup=kb)
        return
    client_manager = call.bot.get("google_client_manager")
    type_user = get_type_user(call.from_user.id)
    days = await get_free_days(client_manager, get_names(call.from_user.id), type_user)
    text = "Выберите дни" if days else "Нет доступных дней для записи"
    kb = kb_inline.kb_days(days) if days else kb_inline.kb_start(clear=True, free_days=False)
    await state.update_data(free_days=days)
    await call.message.edit_text(text, reply_markup=kb)
    await state.update_data(days=[])
    if days:
        await state.set_state("select_days")


# handler
async def select_days(call: CallbackQuery, callback_data: dict, state: FSMContext):
    await call.answer()
    data = await state.get_data()
    make = callback_data.get("make")
    if make != "next":
        if make == "select":
            data["days"].append(callback_data["day"])
        elif make == "cancel":
            data["days"].remove(callback_data["day"])
        await state.update_data(days=data["days"])
        kb = kb_inline.kb_days(data["free_days"], data["days"])
        await call.message.edit_reply_markup(reply_markup=kb)
    if len(data["days"]) == 5 or make == "next":
        data["days"].sort(key=lambda x: service.DAYS.index(x))
        type_user = get_type_user(call.from_user.id)
        days_with_intervals = service.get_intervals(data["days"], type_user)
        day = days_with_intervals.pop(0)
        type_user = get_type_user(call.from_user.id)
        kb = kb_inline.kb_intervals(day.intervals, day.day, call.from_user.id, type_user)
        await state.update_data({"days": days_with_intervals, "selected": dict()})
        await call.message.edit_text(f"Выберите интервал на <u>{day.day.capitalize()}</u>", reply_markup=kb)
        await state.set_state("choice_interval")


def create_text_after_record(start_text: str, records: dict) -> str:
    """Формирует текст после записи в таблицу."""
    text = start_text
    for day, interval in records.items():
        text += f"\n<u>{day.capitalize()}</u> - <b>{interval}</b>"
    return text


# handler
async def choice_interval(call: CallbackQuery, callback_data: dict, state: FSMContext):
    client_manager = call.bot.get("google_client_manager")
    client = await client_manager.authorize()
    # selected_day = {callback_data["day"]: callback_data["interval"].replace(".", ":")}
    data = await state.get_data()
    data["selected"][callback_data["day"]] = callback_data["interval"].replace(".", ":")
    if len(data["days"]) == 0:
        await call.message.edit_text("Записываем данные в таблицу")
        name = get_names(call.from_user.id)
        worksheet = await get_worksheet(client)
        recorded_shifts = await service.get_all_cell_by_name(worksheet, name)
        if len(recorded_shifts) + len(data["selected"]) > 5:
            await call.message.answer(f"Вы можете записаться на {5 - len(recorded_shifts)} дн.\n"
                                      f"или нажмите сбросить пожелания по графику")
            kb = kb_inline.kb_start(True)
            text = 'Нажмите "Пожелания по графику", чтобы отметить смены\n' \
                   'Нажмите "Сбросить пожелания по графику", чтобы сбросить все пожелания'
            await call.message.answer(text, reply_markup=kb)
            await state.finish()
            return
        type_user = get_type_user(call.from_user.id)
        missed_records, marked_records = await service.write_intervals(data["selected"], name, type_user, worksheet)
        if missed_records:
            text = create_text_after_record("Нет свободных мест на следующие дни:", missed_records)
            await call.message.answer(text)
        if marked_records:
            text = create_text_after_record("Следующие смены занесены в таблицу", marked_records)
            await call.message.answer(text)
        await state.finish()
        text, kb = await check_records_in_table(client, call.from_user.id)
        await call.message.answer(text, reply_markup=kb)
        return
    day_with_intervals = data["days"].pop(0)
    type_user = get_type_user(call.from_user.id)
    kb = kb_inline.kb_intervals(day_with_intervals.intervals, day_with_intervals.day, call.from_user.id, type_user)
    await state.update_data({"days": data["days"], "selected": data["selected"]})
    await call.message.edit_text(f"Выберите интервал на <u>{day_with_intervals.day.capitalize()}</u>", reply_markup=kb)


def register_user(dp: Dispatcher):
    dp.register_message_handler(handler_cmd_start, commands=["start"], state="*")
    dp.register_callback_query_handler(handler_clear_preferences, lambda call: call.data == "clear")
    dp.register_callback_query_handler(handler_select_preferences, lambda call: call.data == "start")
    dp.register_callback_query_handler(show_my_preferences, lambda call: call.data == "show")
    dp.register_callback_query_handler(select_days, kb_inline.callback_days.filter(), state="select_days")
    dp.register_callback_query_handler(choice_interval, kb_inline.callback_data_intervals.filter(),
                                       state="choice_interval")
