from datetime import datetime
from sqlalchemy import String, Integer, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class Child(Base):
    __tablename__ = "children"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(50))
    level: Mapped[int] = mapped_column(Integer, default=1)
    streak: Mapped[int] = mapped_column(Integer, default=0)       # серия правильных
    wrong_streak: Mapped[int] = mapped_column(Integer, default=0) # серия ошибок подряд
    points: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    sessions: Mapped[list["Session"]] = relationship(back_populates="child")
    rewards: Mapped[list["RewardRequest"]] = relationship(back_populates="child")


class Session(Base):
    __tablename__ = "sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    child_id: Mapped[int] = mapped_column(ForeignKey("children.id"))
    topic: Mapped[str] = mapped_column(String(50))
    question: Mapped[str] = mapped_column(String(500))
    correct_answer: Mapped[int] = mapped_column(Integer)
    user_answer: Mapped[int] = mapped_column(Integer)
    is_correct: Mapped[bool] = mapped_column(Boolean)
    points_earned: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    child: Mapped["Child"] = relationship(back_populates="sessions")


class RewardRequest(Base):
    __tablename__ = "reward_requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    child_id: Mapped[int] = mapped_column(ForeignKey("children.id"))
    reward_name: Mapped[str] = mapped_column(String(100))
    reward_emoji: Mapped[str] = mapped_column(String(10))
    points_cost: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    child: Mapped["Child"] = relationship(back_populates="rewards")
