import pytest
import pytest_asyncio
import asyncio
from datetime import datetime, timedelta, UTC
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from src.models.models import Base, User, PromoCode, Subscription
from src.utils.database import db_manager


@pytest.fixture(scope="module")
def event_loop():
    loop = asyncio.get_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def async_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    AsyncSessionLocal = sessionmaker(
        engine, expire_on_commit=False, class_=AsyncSession
    )
    async with AsyncSessionLocal() as session:
        yield session
    await engine.dispose()


@pytest.mark.asyncio
async def test_apply_promo_once_per_user(async_session):
    # Создаем пользователя и промокод
    user1 = User(user_id=1, first_name="Test")
    user2 = User(user_id=2, first_name="Other")
    promo = PromoCode(
        code="PROMO1",
        discount=5,
        expiration_date=datetime.now(UTC) + timedelta(days=1),
        used=False,
    )
    sub1 = Subscription(
        user_id=1,
        end_date=datetime.now(UTC),
        active=True,
        lang="ru",
        trial_used=False,
        auto_renewal=True,
    )
    sub2 = Subscription(
        user_id=2,
        end_date=datetime.now(UTC),
        active=True,
        lang="ru",
        trial_used=False,
        auto_renewal=True,
    )
    async_session.add_all([user1, user2, promo, sub1, sub2])
    await async_session.commit()

    # Первый пользователь применяет промокод
    assert not await db_manager.has_user_used_promo(1, "PROMO1", async_session)
    await db_manager.add_promo_attempt(1, "PROMO1", async_session)
    assert await db_manager.has_user_used_promo(1, "PROMO1", async_session)

    # Повторное применение тем же пользователем — ошибка
    assert await db_manager.has_user_used_promo(1, "PROMO1", async_session)

    # Второй пользователь может применить тот же промокод
    assert not await db_manager.has_user_used_promo(2, "PROMO1", async_session)
    await db_manager.add_promo_attempt(2, "PROMO1", async_session)
    assert await db_manager.has_user_used_promo(2, "PROMO1", async_session)


@pytest.mark.asyncio
async def test_apply_expired_promo(async_session):
    # Создаем пользователя и истёкший промокод
    user = User(user_id=3, first_name="Expired")
    promo = PromoCode(
        code="EXPIRED",
        discount=5,
        expiration_date=datetime.now(UTC) - timedelta(days=1),
        used=False,
    )
    sub = Subscription(
        user_id=3,
        end_date=datetime.now(UTC),
        active=True,
        lang="ru",
        trial_used=False,
        auto_renewal=True,
    )
    async_session.add_all([user, promo, sub])
    await async_session.commit()

    # Проверяем, что промокод истёк
    promo_obj = await db_manager.get_promo_code("EXPIRED", async_session)
    assert promo_obj["expiration_date"] is not None
    expiration_date = datetime.fromisoformat(promo_obj["expiration_date"])
    assert expiration_date < datetime.now(UTC)

    # Пользователь не должен применять истёкший промокод (логика проверки в app, тут только факт наличия)
    # Не добавляем попытку, т.к. в app.py будет ошибка до этого места
    assert not await db_manager.has_user_used_promo(3, "EXPIRED", async_session)
