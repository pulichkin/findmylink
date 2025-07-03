#!/usr/bin/env python3
"""
Тест новой логики бота:
- /start теперь показывает /help
- /get_trial выдает триал
"""

import asyncio
import sys
import os

# Добавляем путь к src
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.handlers.handlers import start, get_trial, help_command
from unittest.mock import AsyncMock, MagicMock

class MockUpdate:
    def __init__(self, user_id=12345, chat_id=12345, language_code="ru"):
        self.effective_user = MagicMock()
        self.effective_user.id = user_id
        self.effective_user.language_code = language_code
        self.effective_chat = MagicMock()
        self.effective_chat.id = chat_id
        self.message = MagicMock()
        self.message.reply_text = AsyncMock()

class MockContext:
    def __init__(self):
        pass

async def test_start_command():
    """Тест команды /start"""
    print("🧪 Тестируем команду /start...")
    
    update = MockUpdate()
    context = MockContext()
    
    # Мокаем help_command
    original_help = help_command
    help_command_mock = AsyncMock()
    
    # Временно заменяем help_command
    import src.handlers.handlers
    src.handlers.handlers.help_command = help_command_mock
    
    try:
        await start(update, context)
        
        # Проверяем, что help_command был вызван
        if help_command_mock.called:
            print("✅ /start успешно вызывает /help")
        else:
            print("❌ /start не вызывает /help")
            
    finally:
        # Восстанавливаем оригинальную функцию
        src.handlers.handlers.help_command = original_help

async def test_get_trial_command():
    """Тест команды /get_trial"""
    print("🧪 Тестируем команду /get_trial...")
    
    update = MockUpdate()
    context = MockContext()
    
    # Мокаем get_user_subscription и activate_trial
    from src.handlers.handlers import get_user_subscription, activate_trial
    
    # Сценарий 1: Пользователь без подписки
    print("  📋 Сценарий 1: Пользователь без подписки")
    
    # Мокаем get_user_subscription возвращает None
    original_get_sub = get_user_subscription
    original_activate = activate_trial
    
    get_user_subscription_mock = AsyncMock(return_value=None)
    activate_trial_mock = AsyncMock(return_value="test_token_123")
    
    import src.handlers.handlers
    src.handlers.handlers.get_user_subscription = get_user_subscription_mock
    src.handlers.handlers.activate_trial = activate_trial_mock
    
    try:
        await get_trial(update, context)
        
        # Проверяем, что функции были вызваны
        if get_user_subscription_mock.called and activate_trial_mock.called:
            print("  ✅ /get_trial успешно активирует триал для нового пользователя")
        else:
            print("  ❌ /get_trial не активирует триал")
            
    finally:
        # Восстанавливаем оригинальные функции
        src.handlers.handlers.get_user_subscription = original_get_sub
        src.handlers.handlers.activate_trial = original_activate

async def main():
    print("🚀 Запуск тестов новой логики бота...\n")
    
    await test_start_command()
    print()
    await test_get_trial_command()
    
    print("\n✅ Тесты завершены!")

if __name__ == "__main__":
    asyncio.run(main()) 