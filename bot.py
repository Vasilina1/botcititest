import asyncio
import logging

import gspread_asyncio
from aiogram import Bot, Dispatcher
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.types import BotCommand, BotCommandScopeChat
from aiogram.utils.exceptions import ChatNotFound

from tgbot.config import load_config
# from tgbot.filters.admin import AdminFilter
from tgbot.handlers.user import register_user
# from tgbot.services.database import create_db_session
from tgbot.misc.logger import setup_logger


# def register_all_middlewares(dp):
#     dp.setup_middleware(DbMiddleware())


# def register_all_filters(dp):
#     dp.filters_factory.bind(AdminFilter)


def register_all_handlers(dp):
    register_user(dp)


async def set_commands(dp: Dispatcher):
    """Установка команд в боте отедельно для админов и обычных пользователей."""
    config = dp.bot.get('config')
    admin_ids = config.tg_bot.admin_ids
    await dp.bot.set_my_commands(
        commands=[BotCommand('start', 'Старт')]
    )
    commands_for_admin = [
        BotCommand('start', 'Старт'),
    ]
    for admin_id in admin_ids:
        try:
            await dp.bot.set_my_commands(
                commands=commands_for_admin,
                scope=BotCommandScopeChat(admin_id)
            )
        except ChatNotFound as er:
            logging.error(f'Установка команд для администратора {admin_id}: {er}')


async def main():
    setup_logger('INFO')
    logging.info('Starting bot')
    config = load_config('.env')
    storage = MemoryStorage()
    bot = Bot(token=config.tg_bot.token, parse_mode='HTML')
    dp = Dispatcher(bot, storage=storage)

    bot['config'] = config
    google_client_manager = gspread_asyncio.AsyncioGspreadClientManager(
        config.misc.scoped_credentials
    )
    bot["google_client_manager"] = google_client_manager

    # bot['db'] = await create_db_session(config)
    bot_info = await bot.get_me()
    logging.info(f'<yellow>Name: <b>{bot_info["first_name"]}</b>, username: {bot_info["username"]}</yellow>')

    # register_all_filters(dp)
    register_all_handlers(dp)
    await set_commands(dp)

    # start
    try:
        await dp.start_polling()
    finally:
        await dp.storage.close()
        await dp.storage.wait_closed()
        # await bot.session.close()


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.error("Bot stopped!")
