#!/usr/bin/env python3
import requests


def test_jwt_auth():
    """Тест для проверки JWT авторизации"""

    # URL API
    base_url = "http://localhost:8080"

    # Тестовые данные от Telegram Login Widget
    test_data = {
        "id": 123456789,
        "first_name": "Test",
        "last_name": "User",
        "username": "testuser",
        "photo_url": "https://t.me/i/userpic/320/testuser.jpg",
        "auth_date": 1234567890,
        "hash": "test_hash",
    }

    print("Тестируем JWT авторизацию...")

    try:
        # 1. Тестируем auth telegram эндпоинт
        print("\n1. Тестируем /api/v1/auth/telegram")
        response = requests.post(
            f"{base_url}/api/v1/auth/telegram",
            headers={"Content-Type": "application/json"},
            json=test_data,
            timeout=5,
        )

        print(f"Статус: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"Получен токен: {data.get('token', 'Нет токена')}")
            print(f"User ID: {data.get('user_id', 'Нет ID')}")

            # 2. Тестируем защищенный эндпоинт с токеном
            token = data.get("token")
            if token:
                print("\n2. Тестируем /api/v1/profile с токеном")
                profile_response = requests.get(
                    f"{base_url}/api/v1/profile",
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {token}",
                    },
                    timeout=5,
                )

                print(f"Статус профиля: {profile_response.status_code}")
                if profile_response.status_code == 200:
                    profile_data = profile_response.json()
                    print(f"Профиль получен: {profile_data}")
                else:
                    print(f"Ошибка профиля: {profile_response.text}")

        else:
            print(f"Ошибка авторизации: {response.text}")

    except Exception as e:
        print(f"Ошибка: {e}")


if __name__ == "__main__":
    test_jwt_auth()
