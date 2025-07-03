import os
import shutil
import logging
from datetime import datetime
from glob import glob
from typing import Optional, List, Tuple
from src.configs.config import config

logger = logging.getLogger(__name__)

class BackupManager:
    """Менеджер для работы с бэкапами базы данных"""

    def __init__(self, database_path: str = None, backup_dir: str = None):
        self.database_path = database_path or config.database.path
        # Используем config.backup.dir, если он есть
        self.backup_dir = backup_dir or getattr(config, 'backup', {}).get('dir', 'backups')
        self.bot = None  # Будет установлен позже

    def set_bot(self, bot):
        """Устанавливает экземпляр бота для работы с Telegram"""
        self.bot = bot

    def ensure_backup_dir(self) -> bool:
        """Создает директорию для бэкапов если её нет"""
        try:
            if not os.path.exists(self.backup_dir):
                os.makedirs(self.backup_dir)
            return True
        except Exception as e:
            logger.error(f"Failed to create backup directory: {e}")
            return False

    def get_backup_files(self) -> List[str]:
        """Возвращает список всех файлов бэкапов, отсортированных по дате (новые первыми)"""
        try:
            pattern = os.path.join(self.backup_dir, "subscriptions_backup_*.db")
            backup_files = sorted(glob(pattern), reverse=True)
            return backup_files
        except Exception as e:
            logger.error(f"Failed to get backup files: {e}")
            return []

    def get_latest_backup(self) -> Optional[str]:
        """Возвращает путь к последнему бэкапу"""
        backup_files = self.get_backup_files()
        return backup_files[0] if backup_files else None

    async def get_latest_backup_from_admins(self) -> Optional[str]:
        """
        Ищет самый свежий бэкап в чатах с админами и скачивает его

        Returns:
            Optional[str]: Путь к скачанному файлу или None
        """
        if not self.bot:
            logger.error("Bot instance not set")
            return None

        try:
            # Создаем директорию для бэкапов
            self.ensure_backup_dir()

            latest_backup_path = None
            latest_backup_date = None

            # Проходим по всем админам
            for admin_id in config.telegram.admin_ids:
                try:
                    # Получаем последние сообщения из чата с админом
                    # Используем get_updates для получения последних сообщений
                    updates = await self.bot.get_updates(limit=100, timeout=1)

                    for update in updates:
                        if (update.message and
                            update.message.chat.id == admin_id and
                            update.message.document and
                            update.message.document.file_name and
                            update.message.document.file_name.startswith("subscriptions_backup_") and
                            update.message.document.file_name.endswith(".db")):

                            # Извлекаем дату из имени файла
                            filename = update.message.document.file_name
                            date_str = filename.replace("subscriptions_backup_", "").replace(".db", "")

                            try:
                                # Парсим дату
                                if "_" in date_str:  # Формат с временем YYYYMMDD_HHMMSS
                                    file_date = datetime.strptime(date_str, "%Y%m%d_%H%M%S")
                                else:  # Формат только с датой YYYYMMDD
                                    file_date = datetime.strptime(date_str, "%Y%m%d")

                                # Проверяем, является ли этот бэкап новее
                                if latest_backup_date is None or file_date > latest_backup_date:
                                    # Скачиваем файл
                                    file_info = await self.bot.get_file(update.message.document.file_id)
                                    download_path = os.path.join(self.backup_dir, filename)

                                    # Скачиваем файл
                                    await file_info.download_to_drive(download_path)

                                    # Если у нас уже был скачанный файл, удаляем его
                                    if latest_backup_path and os.path.exists(latest_backup_path):
                                        os.remove(latest_backup_path)

                                    latest_backup_path = download_path
                                    latest_backup_date = file_date
                                    logger.info(f"Downloaded backup from admin {admin_id}: {filename}")

                            except ValueError as e:
                                logger.warning(f"Invalid date format in filename {filename}: {e}")
                                continue

                except Exception as e:
                    logger.error(f"Error checking admin {admin_id} for backups: {e}")
                    continue

            return latest_backup_path

        except Exception as e:
            logger.error(f"Error getting latest backup from admins: {e}")
            return None

    def create_backup(self, include_time: bool = True) -> Tuple[bool, Optional[str]]:
        """
        Создает бэкап базы данных

        Args:
            include_time: Если True, добавляет время к имени файла

        Returns:
            Tuple[bool, Optional[str]]: (успех, путь к файлу бэкапа)
        """
        try:
            if not self.ensure_backup_dir():
                return False, None

            if not os.path.exists(self.database_path):
                logger.error(f"Database file not found: {self.database_path}")
                return False, None

            # Генерируем имя файла
            if include_time:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            else:
                timestamp = datetime.now().strftime("%Y%m%d")

            backup_filename = f"subscriptions_backup_{timestamp}.db"
            backup_path = os.path.join(self.backup_dir, backup_filename)

            # Копируем базу данных
            shutil.copy2(self.database_path, backup_path)

            logger.info(f"Backup created: {backup_path}")
            return True, backup_path

        except Exception as e:
            logger.error(f"Failed to create backup: {e}")
            return False, None

    def restore_from_backup(self, backup_path: str = None) -> bool:
        """
        Восстанавливает базу данных из бэкапа

        Args:
            backup_path: Путь к файлу бэкапа. Если None, используется последний бэкап

        Returns:
            bool: Успех операции
        """
        try:
            if backup_path is None:
                backup_path = self.get_latest_backup()

            if not backup_path or not os.path.exists(backup_path):
                logger.error(f"Backup file not found: {backup_path}")
                return False

            # Создаем директорию для базы данных если её нет
            os.makedirs(os.path.dirname(self.database_path), exist_ok=True)

            # Копируем бэкап в место основной базы
            shutil.copy2(backup_path, self.database_path)

            logger.info(f"Database restored from backup: {backup_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to restore from backup: {e}")
            return False

    async def auto_restore_if_needed(self) -> bool:
        """
        Автоматически восстанавливает базу данных из последнего бэкапа, если основной файл отсутствует

        Returns:
            bool: True если восстановление прошло успешно или база уже существует
        """
        logger.info(self.database_path)
        if os.path.exists(self.database_path):
            logger.info("Database file exists, no restoration needed")
            return True

        logger.warning(f"Database file not found: {self.database_path}")

        # Сначала проверяем локальные бэкапы
        backup_files = self.get_backup_files()
        if backup_files:
            latest_backup = backup_files[0]
            success = self.restore_from_backup(latest_backup)
            if success:
                logger.info(f"Database restored from local backup: {latest_backup}")
                return True

        # Если локальных бэкапов нет, ищем в чатах с админами
        logger.info("No local backups found, searching in admin chats...")
        if self.bot:
            latest_backup_path = await self.get_latest_backup_from_admins()
            if latest_backup_path:
                success = self.restore_from_backup(latest_backup_path)
                if success:
                    logger.info(f"Database restored from admin chat backup: {latest_backup_path}")
                    return True

        logger.error("No backup files found for restoration")
        return False

    def cleanup_old_backups(self, keep_days: int = 30) -> int:
        """
        Удаляет старые бэкапы, оставляя только за последние N дней

        Args:
            keep_days: Количество дней для хранения бэкапов

        Returns:
            int: Количество удаленных файлов
        """
        try:
            backup_files = self.get_backup_files()
            if not backup_files:
                return 0

            cutoff_date = datetime.now().timestamp() - (keep_days * 24 * 3600)
            deleted_count = 0

            for backup_file in backup_files:
                file_time = os.path.getmtime(backup_file)
                if file_time < cutoff_date:
                    try:
                        os.remove(backup_file)
                        deleted_count += 1
                        logger.info(f"Deleted old backup: {backup_file}")
                    except Exception as e:
                        logger.error(f"Failed to delete old backup {backup_file}: {e}")

            return deleted_count

        except Exception as e:
            logger.error(f"Failed to cleanup old backups: {e}")
            return 0

# Глобальный экземпляр менеджера бэкапов
backup_manager = BackupManager()
