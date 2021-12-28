from collections import namedtuple
from datetime import datetime, timedelta
from typing import Optional, Union

import gspread
from gspread_asyncio import AsyncioGspreadWorksheet, AsyncioGspreadClient, AsyncioGspreadClientManager

from tgbot.services.google_sheets import google_sheets

INTERVALS = {
    "manager": {
        "weekdays": {
            "02:00-10:30": 2,
            "05:00-13:30": 2,
            "06:00-14:30(с)": 1,
            "07:00-15:30": 6,
            "08:00-16:30": 11,
            "10:00-18:30": 9,
            "13:00-21:30": 9,
            "14:30-23:00": 1,
            "14:30-23:00(с)": 1,
            "15:30-00:00(с)": 1,
            "15:30-00:00": 2,
            "17:30-02:00": 1,
            "7-8-10": 15,
            "БЕЗ РАЗНИЦЫ": float("inf"),
        },
        "weekend": {
            "02:00-10:30": 1,
            "06:00-14:30(с)": 1,
            "08:00-16:30": 2,
            "10:00-18:30": 3,
            "11:00-19:30": 3,
            "13:00-21:30": 3,
            "14:30-23:00": 1,
            "14:30-23:00(с)": 1,
            "15:30-00:00(с)": 1,
            "17:30-02:00": 1,
            "БЕЗ РАЗНИЦЫ": float("inf"),
        }
    },
    "dispatcher": {
        "weekdays": {
            "02:00-10:30": 2,
            "08:00-16:30": 1,
            "11:00-19:30": 1,
            "17:30-02:00": 1,
            "БЕЗ РАЗНИЦЫ": float("inf"),
        },
        "weekend": {
            "02:00-10:30": 2,
            "08:00-16:30": 1,
            "11:00-19:30": 1,
            "17:30-02:00": 1,
            "БЕЗ РАЗНИЦЫ": float("inf"),
        }
    }
}

DAYS = ("пн", "вт", "ср", "чт", "пт", "сб", "вс",)
IntervalsDay = namedtuple("IntervalsDay", "day, intervals")


def get_intervals(selected_days: list, type_user) -> list['IntervalsDay']:
    """Получает интервалы для каждого дня"""
    days = []
    for day in selected_days:
        intervals = INTERVALS[type_user]["weekdays"] if day in DAYS[:5] else INTERVALS[type_user]["weekend"]
        days.append(IntervalsDay(day=day, intervals=intervals))
    return days


def is_weekday(day: str) -> bool:
    """Проверяет является ли день выходным"""
    return day not in ("сб", "вс")


def get_name_columns_with_intervals(type_user) -> tuple:
    """Возвращает адреса колонок со сменами в зависимости от типа пользователя"""
    if type_user == "manager":
        return "A", "G"
    return "K", "Q"


async def get_limit_and_cell_by_interval(day, interval, type_user, worksheet) -> tuple[gspread.Cell, int]:
    """Получает ячейку в которой находится интервал и лимит этого интервала"""
    cells = await worksheet.findall(interval)
    name_columns_with_intervals = get_name_columns_with_intervals(type_user)
    if is_weekday(day):
        interval_limits = INTERVALS[type_user]["weekdays"][interval]
        cell = [cell for cell in cells if cell.address.startswith(name_columns_with_intervals[0])][0]
    else:
        interval_limits = INTERVALS[type_user]["weekend"][interval]
        cell = [cell for cell in cells if cell.address.startswith(name_columns_with_intervals[1])][0]
    return cell, interval_limits


columns_day = {
    "manager": (
        {"пн": "B", "вт": "C", "ср": "D", "чт": "E", "пт": "F", "сб": "H", "вс": "I"},
        {"пн": 2, "вт": 3, "ср": 4, "чт": 5, "пт": 6, "сб": 8, "вс": 9}
    ),
    "dispatcher": (
        {"пн": "L", "вт": "N", "ср": "N", "чт": "O", "пт": "P", "сб": "R", "вс": "S"},
        {"пн": 12, "вт": 13, "ср": 14, "чт": 15, "пт": 16, "сб": 18, "вс": 19}
    )
}


async def get_row_col_for_write(day: str, start_row: int, limit: int, type_user: str,
                                worksheet: AsyncioGspreadWorksheet) -> Optional[tuple[int, int]]:
    """Получает ряд и колонку для записи по дню"""
    manager_day_columns, manager_day_int_columns = columns_day.get(type_user)
    column = manager_day_columns[day]
    data = await worksheet.get_values(
        range_name=f"{column}{start_row}:{column}{(start_row + limit - 1) if limit != float('inf') else ''}",
        major_dimension="COLUMNS"
    )
    if not data:
        return start_row, manager_day_int_columns[day]
    if len(data[0]) < limit:
        return start_row + len(data[0]), manager_day_int_columns[day]
    index_free_place = data[0].index("")
    if index_free_place != -1:
        return start_row + index_free_place, manager_day_int_columns[day]


async def write_intervals(day_with_interval: dict, username: str, type_user: str, worksheet: AsyncioGspreadWorksheet):
    """Записывает данные в таблицу. Возвращает день интервал, которые не записал из-за превышенного лимита"""
    missed_records = {}
    marked_records = {}
    cells = []
    for day, interval in day_with_interval.items():
        cell, interval_limits = await get_limit_and_cell_by_interval(day, interval, type_user, worksheet)
        row = cell.row
        # "14:30-23:00(с)", "15:30-00:00(с)"
        if interval in ("14:30-23:00(с)", "15:30-00:00(с)"):
            interval_limits = 2
            row = row if interval == "14:30-23:00(с)" else row - 1
        row_col = await get_row_col_for_write(day, row, interval_limits, type_user, worksheet)
        if not row_col:
            missed_records[day] = interval
            continue
        if interval in ("14:30-23:00(с)", "15:30-00:00(с)") and row_col[0] != row:
            missed_records[day] = interval
            continue
        row = row_col[0] if interval != "15:30-00:00(с)" else row_col[0] + 1
        cell = gspread.Cell(row, row_col[1], username)
        cells.append(cell)
        marked_records[day] = interval
    if cells:
        await worksheet.update_cells(cells)
    return missed_records, marked_records


async def get_all_cell_by_name(worksheet: AsyncioGspreadWorksheet, name: str):
    """Возвращает все ячейки, по имени"""
    cells = await worksheet.findall(name)
    return cells


async def clear_preferences(client: AsyncioGspreadClient, firstname: str):
    """Удаляет все записи с именем firstname из таблицы"""
    worksheet = await google_sheets.get_worksheet(client)
    cells = await get_all_cell_by_name(worksheet, firstname)
    if not cells:
        return
    for cell in cells:
        cell.value = ""
    await worksheet.update_cells(cells)


async def get_free_days(worksheet: AsyncioGspreadWorksheet, name: str, type_user: str) -> Union[list, None]:
    """Возвращает списко дней, в которые не записан пользователь. Если таких дней меньше трех, возрвращает None"""
    columns_with_days = {"manager": ["B:F", "H:I"], "dispatcher": ["L:P", "R:S"]}
    days = await worksheet.batch_get(columns_with_days[type_user], "COLUMNS")
    free_days = []
    for day in days[0] + days[1]:
        if name not in day:
            free_days.append(day[0].lower())
    return free_days if len(free_days) > 2 else None


# Функции проверки, можно ли сейчас пользоваться ботом
def get_start_time(now: datetime) -> datetime:
    """Возвращает стартовое время работы бота - текущий понедельник 00:00"""
    monday = now - timedelta(days=now.weekday())
    return datetime(year=monday.year, month=monday.month, day=monday.day)


def get_end_time(now: datetime) -> datetime:
    """Возвращает время окончания работы бота на этой неделе - текущая пятница 16:00"""
    day = 4 - now.weekday()
    friday = now + timedelta(days=day)
    return datetime(year=friday.year, month=friday.month, day=friday.day, hour=16)


def time_in_range() -> bool:
    """Возвращает True если текущее время в рабочем диапазоне и False если нет"""
    now = datetime.now()
    start = get_start_time(now)
    end = get_end_time(now)
    return start <= now <= end


# Функции показа смен
def replace_empty_value_in_list(shifts: list) -> list[str]:
    """Заменяет пустые значиния в данных о интервалах интервалами, которые относятся к этим ячейкам"""
    list_shifts = []
    shift = shifts[0]
    for value in shifts[0]:
        list_shifts.append(value if value != "" else shift)
        if value != "":
            shift = value
    return list_shifts


def parse_user_shifts(data: list[list], username: str) -> dict:
    """Парсит данные таблицы для поиска смен пользователя"""
    week_day_shifts = data[0]
    weekend_day_shifts = data[6]
    result = {}
    for index, column in enumerate(data[1:6] + data[7:]):
        if index < 5:
            matching = zip(week_day_shifts, column)
        else:
            matching = zip(weekend_day_shifts, column)
        for i in matching:
            if i[1] == username:
                result[column[0]] = i[0]
    return result


async def get_user_shifts(google_manager: AsyncioGspreadClientManager, username: str, type_user: str) -> dict:
    """Возвращает список записанных смен пользователя"""
    client = await google_manager.authorize()
    worksheet = await google_sheets.get_worksheet(client)
    columns = {"manager": "A:I", "dispatcher": "K:S"}
    shifts = await worksheet.get_values(columns[type_user], "COLUMNS")
    return parse_user_shifts(shifts, username)


# Функции для тестирования
# import asyncio
# async def main():
#     client = await google_sheets.get_autorize_google_client()
#     await get_user_shifts(client, "asdf")

# asyncio.run(main())
