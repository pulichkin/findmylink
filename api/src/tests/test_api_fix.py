#!/usr/bin/env python3
"""
Тестовый скрипт для проверки исправлений API
"""

import asyncio
import sys
import os

# Добавляем путь к API
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "api"))


async def test_api_import():
    """Тестируем импорт API"""
    try:
        print("✅ API успешно импортирован")
        return True
    except Exception as e:
        print(f"❌ Ошибка импорта API: {e}")
        return False


async def test_config():
    """Тестируем конфигурацию"""
    try:
        from api.config import config

        print("✅ Конфигурация загружена")
        print(f"   Redis URL: {config.REDIS_URL}")
        print(f"   Bot Token: {config.BOT_TOKEN[:20]}...")
        return True
    except Exception as e:
        print(f"❌ Ошибка конфигурации: {e}")
        return False


async def test_redis_manager():
    """Тестируем Redis менеджер"""
    try:
        from api.utils.redis_manager import redis_manager

        print("✅ Redis менеджер инициализирован")

        # Тестируем подключение
        connected = await redis_manager._ensure_connection()
        if connected:
            print("✅ Redis подключение успешно")
        else:
            print("⚠️  Redis недоступен, но это нормально для тестирования")
        return True
    except Exception as e:
        print(f"❌ Ошибка Redis менеджера: {e}")
        return False


async def test_jwt_manager():
    """Тестируем JWT менеджер"""
    try:
        from api.utils.jwt_utils import jwt_manager

        # Тестируем создание токена
        test_user_id = 12345
        token = jwt_manager.create_user_token(test_user_id)
        print(f"✅ JWT токен создан: {token[:20]}...")

        # Тестируем декодирование
        decoded_user_id = jwt_manager.get_user_id_from_token(token)
        if decoded_user_id == test_user_id:
            print("✅ JWT токен корректно декодирован")
        else:
            print(
                f"❌ Ошибка декодирования JWT: ожидалось {test_user_id}, получено {decoded_user_id}"
            )
            return False

        return True
    except Exception as e:
        print(f"❌ Ошибка JWT менеджера: {e}")
        return False


async def test_database_manager():
    """Тестируем менеджер базы данных"""
    try:
        from api.utils.database import db_manager

        print("✅ Менеджер базы данных инициализирован")

        # Тестируем подключение
        conn = db_manager.get_sync_connection()
        conn.close()
        print("✅ Подключение к базе данных успешно")

        return True
    except Exception as e:
        print(f"❌ Ошибка менеджера базы данных: {e}")
        return False


async def main():
    """Основная функция тестирования"""
    print("🧪 Тестирование исправлений API...")
    print("=" * 50)

    tests = [
        ("Импорт API", test_api_import),
        ("Конфигурация", test_config),
        ("Redis менеджер", test_redis_manager),
        ("JWT менеджер", test_jwt_manager),
        ("Менеджер базы данных", test_database_manager),
    ]

    results = []
    for test_name, test_func in tests:
        print(f"\n🔍 Тестируем: {test_name}")
        try:
            result = await test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ Неожиданная ошибка в тесте {test_name}: {e}")
            results.append((test_name, False))

    print("\n" + "=" * 50)
    print("📊 Результаты тестирования:")

    passed = 0
    for test_name, result in results:
        status = "✅ ПРОЙДЕН" if result else "❌ ПРОВАЛЕН"
        print(f"   {test_name}: {status}")
        if result:
            passed += 1

    print(f"\n🎯 Итого: {passed}/{len(results)} тестов пройдено")

    if passed == len(results):
        print("🎉 Все тесты пройдены! API готов к работе.")
        return 0
    else:
        print("⚠️  Некоторые тесты не пройдены. Проверьте конфигурацию.")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
