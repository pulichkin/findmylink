#!/usr/bin/env python3
"""
Тестовый скрипт для проверки защиты API
"""

import requests
import time
import urllib3

# Отключаем предупреждения о SSL для тестирования
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

API_BASE_URL = "https://findmylink.ru"


def test_unauthorized_access():
    """Тест несанкционированного доступа"""
    print("🔒 Тестирование защиты API...")

    # Тест 1: Попытка доступа без токена
    print("\n1. Попытка доступа без токена:")
    try:
        response = requests.get(f"{API_BASE_URL}/api/v1/profile", verify=False)
        print(f"   Статус: {response.status_code}")
        print("   Ожидаемый статус: 401 (Unauthorized)")
        print(f"   Ответ: {response.text[:100]}...")
        if response.status_code == 401:
            print("   ✅ Защита работает - доступ без токена заблокирован")
        else:
            print("   ❌ Защита не работает - доступ без токена разрешен")
    except Exception as e:
        print(f"   Ошибка: {e}")

    # Тест 2: Попытка доступа с неправильным User-Agent
    print("\n2. Попытка доступа с неправильным User-Agent:")
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Authorization": "Bearer fake-token",
        }
        response = requests.get(
            f"{API_BASE_URL}/api/v1/profile", headers=headers, verify=False
        )
        print(f"   Статус: {response.status_code}")
        print("   Ожидаемый статус: 403 (Forbidden)")
        print(f"   Ответ: {response.text[:100]}...")
        if response.status_code == 403:
            print("   ✅ Защита работает - неправильный User-Agent заблокирован")
        else:
            print("   ❌ Защита не работает - неправильный User-Agent разрешен")
    except Exception as e:
        print(f"   Ошибка: {e}")

    # Тест 3: Попытка доступа с правильным User-Agent но без токена
    print("\n3. Попытка доступа с правильным User-Agent но без токена:")
    try:
        headers = {"User-Agent": "Chrome-Extension/FindMyLink"}
        response = requests.get(
            f"{API_BASE_URL}/api/v1/profile", headers=headers, verify=False
        )
        print(f"   Статус: {response.status_code}")
        print("   Ожидаемый статус: 401 (Unauthorized)")
        print(f"   Ответ: {response.text[:100]}...")
        if response.status_code == 401:
            print(
                "   ✅ Защита работает - правильный User-Agent но без токена заблокирован"
            )
        else:
            print(
                "   ❌ Защита не работает - правильный User-Agent без токена разрешен"
            )
    except Exception as e:
        print(f"   Ошибка: {e}")

    # Тест 4: Попытка доступа с неправильным токеном
    print("\n4. Попытка доступа с неправильным токеном:")
    try:
        headers = {
            "User-Agent": "Chrome-Extension/FindMyLink",
            "Authorization": "Bearer invalid.jwt.token",
        }
        response = requests.get(
            f"{API_BASE_URL}/api/v1/profile", headers=headers, verify=False
        )
        print(f"   Статус: {response.status_code}")
        print("   Ожидаемый статус: 401 (Unauthorized)")
        print(f"   Ответ: {response.text[:100]}...")
        if response.status_code == 401:
            print("   ✅ Защита работает - неправильный токен заблокирован")
        else:
            print("   ❌ Защита не работает - неправильный токен разрешен")
    except Exception as e:
        print(f"   Ошибка: {e}")

    # Тест 5: Попытка доступа к данным другого пользователя
    print("\n5. Попытка доступа к данным другого пользователя:")
    try:
        # Создаем фейковый токен для пользователя 123
        fake_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoxMjMsImV4cCI6MTczNTY4MDAwMH0.fake_signature"
        headers = {
            "User-Agent": "Chrome-Extension/FindMyLink",
            "Authorization": f"Bearer {fake_token}",
        }
        response = requests.get(
            f"{API_BASE_URL}/api/v1/subscription/456", headers=headers, verify=False
        )
        print(f"   Статус: {response.status_code}")
        print("   Ожидаемый статус: 401 или 403")
        print(f"   Ответ: {response.text[:100]}...")
        if response.status_code in [401, 403]:
            print("   ✅ Защита работает - доступ к чужим данным заблокирован")
        else:
            print("   ❌ Защита не работает - доступ к чужим данным разрешен")
    except Exception as e:
        print(f"   Ошибка: {e}")

    # Тест 6: Rate limiting (множественные запросы)
    print("\n6. Тест rate limiting:")
    try:
        headers = {
            "User-Agent": "Chrome-Extension/FindMyLink",
            "Authorization": "Bearer fake-token",
        }
        rate_limit_hit = False
        for i in range(15):
            response = requests.get(
                f"{API_BASE_URL}/api/v1/profile", headers=headers, verify=False
            )
            print(f"   Запрос {i + 1}: {response.status_code}")
            if response.status_code == 429:
                print(f"   ✅ Rate limit сработал на запросе {i + 1}")
                rate_limit_hit = True
                break
            time.sleep(0.1)

        if not rate_limit_hit:
            print("   ❌ Rate limit не сработал после 15 запросов")
    except Exception as e:
        print(f"   Ошибка: {e}")


def test_authorized_access():
    """Тест авторизованного доступа (если есть валидный токен)"""
    print("\n🔑 Тестирование авторизованного доступа...")

    # Здесь можно добавить тесты с валидным токеном
    # Для этого нужно получить реальный токен через Telegram авторизацию
    print("   Требуется валидный токен для полного тестирования")


if __name__ == "__main__":
    test_unauthorized_access()
    test_authorized_access()
    print("\n✅ Тестирование завершено!")
