#!/usr/bin/env python3
import hmac
import hashlib
import json


def test_telegram_signature():
    """Тест для проверки подписи Telegram"""

    # Тестовые данные (как приходят от Telegram Login Widget)
    test_data = {
        "id": 123456789,
        "first_name": "Test",
        "last_name": "User",
        "username": "testuser",
        "photo_url": "https://t.me/i/userpic/320/testuser.jpg",
        "auth_date": 1234567890,
        "hash": "test_hash",
    }

    # Токен бота (замените на реальный)
    bot_token = "7670717961:AAGhgDQQ70j5my8KpOjj19fbpP7q2M9aWHs"

    print("Тестируем подпись Telegram...")
    print(f"Данные: {json.dumps(test_data, indent=2)}")
    print(f"Токен бота: {bot_token}")

    # Создаем строку для проверки подписи
    data_check_string = "\n".join(
        [f"{k}={v}" for k, v in sorted(test_data.items()) if k != "hash"]
    )

    print(f"\nСтрока для проверки: {data_check_string}")

    # Создаем секретный ключ из токена бота
    secret_key = hmac.new(
        bot_token.encode(), "WebAppData".encode(), hashlib.sha256
    ).digest()

    print(f"Секретный ключ (hex): {secret_key.hex()}")

    # Вычисляем ожидаемый хеш
    expected_hash = hmac.new(
        secret_key, data_check_string.encode(), hashlib.sha256
    ).hexdigest()

    print(f"Ожидаемый хеш: {expected_hash}")
    print(f"Полученный хеш: {test_data['hash']}")

    if test_data["hash"] == expected_hash:
        print("✅ Подпись верна!")
    else:
        print("❌ Подпись неверна!")
        print("Возможные причины:")
        print("1. Неправильный токен бота")
        print("2. Неправильный формат данных")
        print("3. Данные были изменены")


if __name__ == "__main__":
    test_telegram_signature()
