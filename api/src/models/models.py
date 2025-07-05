from datetime import datetime, UTC
from typing import Optional, List
from sqlalchemy import ForeignKey, String, Integer, Boolean, DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from msgspec import Struct
from enum import Enum


class Base(DeclarativeBase): ...


class User(Base):
    __tablename__ = "users"

    user_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    first_name: Mapped[str] = mapped_column(String(100))
    last_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    username: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    photo_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    lang: Mapped[str] = mapped_column(String(10), default="ru")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    subscription: Mapped["Subscription"] = relationship(
        back_populates="user", uselist=False
    )
    purchases: Mapped[List["Purchase"]] = relationship(back_populates="user")
    promo_attempts: Mapped[List["PromoAttempt"]] = relationship(back_populates="user")


class SubscriptionType(str, Enum):
    daily = "daily"
    monthly = "monthly"
    quarterly = "quarterly"
    half_yearly = "half-yearly"
    yearly = "yearly"


class Subscription(Base):
    __tablename__ = "subscriptions"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.user_id"), primary_key=True)
    end_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=False)
    lang: Mapped[str] = mapped_column(String(10), default="ru")
    trial_used: Mapped[bool] = mapped_column(Boolean, default=False)
    auto_renewal: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )
    subtype: Mapped[SubscriptionType] = mapped_column(String(20))

    # Relationships
    user: Mapped["User"] = relationship(back_populates="subscription")


class PromoCode(Base):
    __tablename__ = "promo_codes"

    code: Mapped[str] = mapped_column(String(50), primary_key=True)
    discount: Mapped[int] = mapped_column(Integer)  # количество дней
    expiration_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    used: Mapped[bool] = mapped_column(Boolean, default=False)


class PromoAttempt(Base):
    __tablename__ = "promo_attempts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.user_id"))
    code: Mapped[str] = mapped_column(
        String(50)
    )  # Код промокода, который применил пользователь
    attempt_time: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(UTC)
    )

    # Relationships
    user: Mapped["User"] = relationship(back_populates="promo_attempts")


class TelegramAuthData(Struct):
    id: int
    first_name: str
    auth_date: int
    hash: str
    last_name: str = ""
    username: str = ""
    photo_url: str = ""


class TelegramAuthResponse(Struct):
    token: str
    user_id: int
    first_name: str
    last_name: str = ""
    username: str = ""
    photo_url: str = ""


class SubscriptionResponse(Struct):
    user_id: int
    end_date: Optional[str] = None
    active: bool = False
    trial_used: bool = False
    auto_renewal: bool = True
    lang: str = "ru"
    subtype: str = "trial"
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class PromoApplyResponse(Struct):
    message: str
    days_added: int
    new_end_date: str


class ProfileResponse(Struct):
    user_id: int
    first_name: str = ""
    last_name: str = ""
    username: str = ""
    photo_url: str = ""
    subscription: Optional[SubscriptionResponse] = None


class Purchase(Base):
    __tablename__ = "purchases"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.user_id"), nullable=False)
    subscription: Mapped[SubscriptionType] = mapped_column(String(20), nullable=False)
    price: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    # Relationships
    user: Mapped["User"] = relationship(back_populates="purchases")
