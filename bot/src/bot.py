import os
import logging
from telegram import Bot
from telegram.ext import Application, CommandHandler, PreCheckoutQueryHandler, MessageHandler, filters, CallbackQueryHandler

from src.configs.config import config
from src.utils.backup import backup_manager
from src.handlers.handlers import (
    start, subscribe, apply_promo, pre_checkout_query, successful_payment,
    check_subscriptions, status, help_command, unsubscribe, subscriptions,
    subscriptions_callback, create_promo_cmd, delete_promo_cmd,
    create_subscription_cmd, delete_subscription_cmd, get_trial,
    create_backup, scheduled_backup, send_backup
)

# Настройка логирования
if not os.path.exists('logs'):
    os.makedirs('logs')

logging.basicConfig(
    level=getattr(logging, config.logging.level),
    format=config.logging.format,
    handlers=[
        logging.FileHandler(config.logging.file),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Инициализация бота
bot = Bot(token=config.telegram.bot_token)

# Передаем экземпляр бота в BackupManager
backup_manager.set_bot(bot)

async def main():
    application = Application.builder().token(config.telegram.bot_token).build()

    # Автоматическое восстановление базы данных из последнего бэкапа, если основной файл отсутствует
    if not await backup_manager.auto_restore_if_needed():
        logger.error("Failed to restore database from backup. Exiting.")
        return

    # Регистрация обработчиков
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("get_trial", get_trial))
    application.add_handler(CommandHandler("subscribe", subscribe))
    application.add_handler(CommandHandler("create_subscription", create_subscription_cmd))
    application.add_handler(CommandHandler("delete_subscription", delete_subscription_cmd))
    application.add_handler(CommandHandler("promo", apply_promo))
    application.add_handler(CommandHandler("promo_cmd", create_promo_cmd))
    application.add_handler(CommandHandler("delete_promo", delete_promo_cmd))
    application.add_handler(PreCheckoutQueryHandler(pre_checkout_query))
    application.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment))

    # Новые команды
    application.add_handler(CommandHandler("status", status))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("unsubscribe", unsubscribe))
    application.add_handler(CommandHandler("subscriptions", subscriptions))
    application.add_handler(CallbackQueryHandler(subscriptions_callback, pattern="^subscribe_"))
    application.add_handler(CommandHandler("backup", create_backup))
    application.add_handler(CommandHandler("send_backup", send_backup))

    # Периодические задачи
    application.job_queue.run_repeating(check_subscriptions, interval=86400)  # Раз в сутки
    application.job_queue.run_repeating(scheduled_backup, interval=86400)    # Автоматический бэкап раз в сутки

    logger.info("Starting bot polling")
    await application.run_polling()

if __name__ == "__main__":
    import asyncio
    import nest_asyncio
    nest_asyncio.apply()
    loop = asyncio.get_event_loop()
    loop.create_task(main())
    loop.run_forever()
