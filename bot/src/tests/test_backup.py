#!/usr/bin/env python3
"""
Тесты для модуля работы с бэкапами базы данных
"""

import os
import shutil
import tempfile
import unittest
import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

# Добавляем путь к src
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.utils.backup import BackupManager

class TestBackupManager(unittest.TestCase):
    """Тесты для класса BackupManager"""
    
    def setUp(self):
        """Настройка тестового окружения"""
        # Создаем временные директории
        self.temp_dir = tempfile.mkdtemp()
        self.backup_dir = os.path.join(self.temp_dir, "backups")
        self.database_path = os.path.join(self.temp_dir, "test.db")
        
        # Создаем тестовую базу данных
        with open(self.database_path, 'w') as f:
            f.write("test database content")
        
        # Инициализируем менеджер бэкапов
        self.backup_manager = BackupManager(
            database_path=self.database_path,
            backup_dir=self.backup_dir
        )
    
    def tearDown(self):
        """Очистка после тестов"""
        # Удаляем временные файлы
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_ensure_backup_dir(self):
        """Тест создания директории для бэкапов"""
        # Директория не должна существовать
        self.assertFalse(os.path.exists(self.backup_dir))
        
        # Создаем директорию
        result = self.backup_manager.ensure_backup_dir()
        
        # Проверяем результат
        self.assertTrue(result)
        self.assertTrue(os.path.exists(self.backup_dir))
    
    def test_create_backup_success(self):
        """Тест успешного создания бэкапа"""
        # Создаем бэкап
        success, backup_path = self.backup_manager.create_backup(include_time=True)
        
        # Проверяем результат
        self.assertTrue(success)
        self.assertIsNotNone(backup_path)
        self.assertTrue(os.path.exists(backup_path))
        
        # Проверяем содержимое
        with open(backup_path, 'r') as f:
            content = f.read()
        self.assertEqual(content, "test database content")
    
    def test_create_backup_without_time(self):
        """Тест создания бэкапа без времени в имени"""
        success, backup_path = self.backup_manager.create_backup(include_time=False)
        
        self.assertTrue(success)
        self.assertIsNotNone(backup_path)
        
        # Проверяем формат имени файла (только дата, без времени)
        filename = os.path.basename(backup_path)
        self.assertTrue(filename.startswith("subscriptions_backup_"))
        self.assertTrue(filename.endswith(".db"))
        # Должно быть 8 цифр даты (YYYYMMDD)
        date_part = filename.replace("subscriptions_backup_", "").replace(".db", "")
        self.assertEqual(len(date_part), 8)
    
    def test_create_backup_database_not_exists(self):
        """Тест создания бэкапа когда база данных не существует"""
        # Удаляем базу данных
        os.remove(self.database_path)
        
        # Пытаемся создать бэкап
        success, backup_path = self.backup_manager.create_backup()
        
        # Должно вернуть False
        self.assertFalse(success)
        self.assertIsNone(backup_path)
    
    def test_get_backup_files_empty(self):
        """Тест получения списка бэкапов когда их нет"""
        files = self.backup_manager.get_backup_files()
        self.assertEqual(files, [])
    
    def test_get_backup_files_with_backups(self):
        """Тест получения списка бэкапов"""
        # Создаем несколько бэкапов
        self.backup_manager.ensure_backup_dir()
        
        backup1 = os.path.join(self.backup_dir, "subscriptions_backup_20231201.db")
        backup2 = os.path.join(self.backup_dir, "subscriptions_backup_20231202.db")
        
        shutil.copy2(self.database_path, backup1)
        shutil.copy2(self.database_path, backup2)
        
        # Получаем список файлов
        files = self.backup_manager.get_backup_files()
        
        # Проверяем что файлы найдены и отсортированы (новые первыми)
        self.assertEqual(len(files), 2)
        self.assertIn(backup1, files)
        self.assertIn(backup2, files)
    
    def test_get_latest_backup(self):
        """Тест получения последнего бэкапа"""
        # Создаем несколько бэкапов
        self.backup_manager.ensure_backup_dir()
        
        backup1 = os.path.join(self.backup_dir, "subscriptions_backup_20231201.db")
        backup2 = os.path.join(self.backup_dir, "subscriptions_backup_20231202.db")
        
        shutil.copy2(self.database_path, backup1)
        shutil.copy2(self.database_path, backup2)
        
        # Получаем последний бэкап
        latest = self.backup_manager.get_latest_backup()
        
        # Должен быть самый новый (20231202)
        self.assertEqual(latest, backup2)
    
    def test_restore_from_backup_success(self):
        """Тест успешного восстановления из бэкапа"""
        # Создаем бэкап
        self.backup_manager.ensure_backup_dir()
        backup_path = os.path.join(self.backup_dir, "subscriptions_backup_20231201.db")
        shutil.copy2(self.database_path, backup_path)
        
        # Удаляем основную базу
        os.remove(self.database_path)
        
        # Восстанавливаем из бэкапа
        success = self.backup_manager.restore_from_backup(backup_path)
        
        # Проверяем результат
        self.assertTrue(success)
        self.assertTrue(os.path.exists(self.database_path))
        
        # Проверяем содержимое
        with open(self.database_path, 'r') as f:
            content = f.read()
        self.assertEqual(content, "test database content")
    
    def test_restore_from_latest_backup(self):
        """Тест восстановления из последнего бэкапа"""
        # Создаем несколько бэкапов
        self.backup_manager.ensure_backup_dir()
        
        backup1 = os.path.join(self.backup_dir, "subscriptions_backup_20231201.db")
        backup2 = os.path.join(self.backup_dir, "subscriptions_backup_20231202.db")
        
        shutil.copy2(self.database_path, backup1)
        shutil.copy2(self.database_path, backup2)
        
        # Удаляем основную базу
        os.remove(self.database_path)
        
        # Восстанавливаем из последнего бэкапа
        success = self.backup_manager.restore_from_backup()
        
        # Проверяем результат
        self.assertTrue(success)
        self.assertTrue(os.path.exists(self.database_path))
    
    def test_auto_restore_if_needed_database_exists(self):
        """Тест автовосстановления когда база существует"""
        # База существует
        self.assertTrue(os.path.exists(self.database_path))
        
        # Автовосстановление должно вернуть True
        result = asyncio.run(self.backup_manager.auto_restore_if_needed())
        self.assertTrue(result)
    
    def test_auto_restore_if_needed_with_local_backup(self):
        """Тест автовосстановления из локального бэкапа"""
        # Создаем бэкап
        self.backup_manager.ensure_backup_dir()
        backup_path = os.path.join(self.backup_dir, "subscriptions_backup_20231201.db")
        shutil.copy2(self.database_path, backup_path)
        
        # Удаляем основную базу
        os.remove(self.database_path)
        
        # Автовосстановление
        result = asyncio.run(self.backup_manager.auto_restore_if_needed())
        
        # Проверяем результат
        self.assertTrue(result)
        self.assertTrue(os.path.exists(self.database_path))
    
    def test_auto_restore_if_needed_no_backup(self):
        """Тест автовосстановления когда нет бэкапов"""
        # Удаляем основную базу
        os.remove(self.database_path)
        
        # Автовосстановление должно вернуть False
        result = asyncio.run(self.backup_manager.auto_restore_if_needed())
        self.assertFalse(result)
    
    @patch('src.utils.backup.config')
    def test_get_latest_backup_from_admins(self, mock_config):
        """Тест получения последнего бэкапа из чатов с админами"""
        mock_config.telegram.admin_ids = [12345, 67890]
        mock_bot = MagicMock()
        self.backup_manager.set_bot(mock_bot)
        
        # Создаем мок обновления с документом
        mock_update = MagicMock()
        mock_update.message = MagicMock()
        mock_update.message.chat.id = 12345
        mock_update.message.document = MagicMock()
        mock_update.message.document.file_name = "subscriptions_backup_20231201_120000.db"
        mock_update.message.document.file_id = "test_file_id"
        
        # Мокаем get_updates
        mock_bot.get_updates = AsyncMock(return_value=[mock_update])
        
        # Мокаем get_file и download_to_drive
        mock_file_info = MagicMock()
        mock_file_info.download_to_drive = AsyncMock()
        mock_bot.get_file = AsyncMock(return_value=mock_file_info)
        
        # Создаем директорию для бэкапов
        self.backup_manager.ensure_backup_dir()
        
        # Тестируем функцию
        result = asyncio.run(self.backup_manager.get_latest_backup_from_admins())
        
        # Проверяем результат
        self.assertIsNotNone(result)
        self.assertTrue(result.endswith("subscriptions_backup_20231201_120000.db"))
        
        # Проверяем что методы были вызваны
        self.assertEqual(mock_bot.get_updates.call_count, 2)  # Для каждого админа
        mock_bot.get_file.assert_called_once_with("test_file_id")
        mock_file_info.download_to_drive.assert_called_once()
    
    def test_cleanup_old_backups(self):
        """Тест очистки старых бэкапов"""
        # Создаем несколько бэкапов
        self.backup_manager.ensure_backup_dir()
        
        backup1 = os.path.join(self.backup_dir, "subscriptions_backup_20231201.db")
        backup2 = os.path.join(self.backup_dir, "subscriptions_backup_20231202.db")
        
        shutil.copy2(self.database_path, backup1)
        shutil.copy2(self.database_path, backup2)
        
        # Мокаем время файлов (делаем backup1 старым)
        old_time = datetime.now().timestamp() - (31 * 24 * 3600)  # 31 день назад
        os.utime(backup1, (old_time, old_time))
        
        # Очищаем старые бэкапы (оставляем за 30 дней)
        deleted_count = self.backup_manager.cleanup_old_backups(keep_days=30)
        
        # Проверяем результат
        self.assertEqual(deleted_count, 1)
        self.assertFalse(os.path.exists(backup1))  # Старый файл удален
        self.assertTrue(os.path.exists(backup2))   # Новый файл остался

if __name__ == '__main__':
    unittest.main() 