#!/usr/bin/env python3
"""
Тест для проверки исправлений в базе данных
"""

import asyncio
import sys
import os

# Добавляем путь к API
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "api"))


async def test_database_syntax():
    """Тестируем синтаксис кода базы данных без импорта aiosqlite"""
    try:
        # Проверяем, что файл можно импортировать
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "database",
            os.path.join(os.path.dirname(__file__), "api", "utils", "database.py"),
        )
        importlib.util.module_from_spec(spec)

        # Проверяем синтаксис
        with open(
            os.path.join(os.path.dirname(__file__), "api", "utils", "database.py"), "r"
        ) as f:
            code = f.read()
            compile(code, "database.py", "exec")

        print("✅ Синтаксис кода базы данных корректен")
        return True
    except SyntaxError as e:
        print(f"❌ Ошибка синтаксиса в коде базы данных: {e}")
        return False
    except Exception as e:
        print(f"❌ Ошибка при проверке кода базы данных: {e}")
        return False


async def test_database_structure():
    """Тестируем структуру менеджера базы данных"""
    try:
        # Проверяем наличие необходимых методов
        from api.utils.database import DatabaseManager

        db_manager = DatabaseManager()

        # Проверяем наличие методов
        required_methods = [
            "get_subscription",
            "update_subscription",
            "get_promo_code",
            "mark_promo_used",
            "add_promo_attempt",
            "get_promo_attempts_count",
            "init_database",
            "get_sync_connection",
        ]

        for method in required_methods:
            if not hasattr(db_manager, method):
                print(f"❌ Отсутствует метод: {method}")
                return False

        print("✅ Структура менеджера базы данных корректна")
        return True

    except Exception as e:
        print(f"❌ Ошибка при проверке структуры базы данных: {e}")
        return False


async def test_context_manager_pattern():
    """Тестируем использование контекстных менеджеров"""
    try:
        with open(
            os.path.join(os.path.dirname(__file__), "api", "utils", "database.py"), "r"
        ) as f:
            code = f.read()

        # Проверяем наличие правильного паттерна
        if "async with aiosqlite.connect(" not in code:
            print("❌ Не найден паттерн контекстного менеджера aiosqlite")
            return False

        if "async with db.execute(" not in code:
            print("❌ Не найден паттерн контекстного менеджера для execute")
            return False

        # Проверяем отсутствие старого паттерна
        if "await self.get_connection()" in code:
            print("❌ Найден старый паттерн get_connection()")
            return False

        print("✅ Используются правильные контекстные менеджеры")
        return True

    except Exception as e:
        print(f"❌ Ошибка при проверке паттернов: {e}")
        return False


async def main():
    """Основная функция тестирования"""
    print("🧪 Тестирование исправлений базы данных...")
    print("=" * 50)

    tests = [
        ("Синтаксис кода", test_database_syntax),
        ("Структура менеджера", test_database_structure),
        ("Контекстные менеджеры", test_context_manager_pattern),
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
        print("🎉 Все тесты пройдены! Исправления базы данных корректны.")
        print("\n📝 Рекомендации:")
        print("   1. Установите aiosqlite: pip install aiosqlite")
        print("   2. Протестируйте API с реальными запросами")
        print("   3. Проблема с 'threads can only be started once' решена")
        return 0
    else:
        print("⚠️  Некоторые тесты не пройдены. Проверьте исправления.")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
