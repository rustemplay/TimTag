from datetime import datetime
from sqlalchemy import String, Integer, Boolean, DateTime, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


# ──────────────────────────────────────────────────────────────
# Вспомогательная функция — дефолтное состояние по предметам
# ──────────────────────────────────────────────────────────────
def default_subjects() -> dict:
    """
    Каждый предмет хранит своё состояние независимо.
    points — очки внутри предмета (суммируются в child.points).
    """
    return {
        "математика": {"level": 1, "streak": 0, "wrong_streak": 0, "points": 0},
        "русский":    {"level": 1, "streak": 0, "wrong_streak": 0, "points": 0},
        "чтение":     {"level": 1, "streak": 0, "wrong_streak": 0, "points": 0},
    }


class Child(Base):
    __tablename__ = "children"

    id:         Mapped[int]      = mapped_column(Integer, primary_key=True)
    name:       Mapped[str]      = mapped_column(String(50))

    # Суммарные очки по всем предметам (отображаются в шапке)
    points:     Mapped[int]      = mapped_column(Integer, default=0)

    # JSON-поле: {subject: {level, streak, wrong_streak, points}}
    subjects:   Mapped[dict]     = mapped_column(JSON, default=default_subjects)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    sessions: Mapped[list["Session"]]       = relationship(back_populates="child")
    rewards:  Mapped[list["RewardRequest"]] = relationship(back_populates="child")

    # ── Удобные property для шаблонов (обратная совместимость) ──

    def subject_state(self, subject: str) -> dict:
        """Возвращает состояние предмета, создаёт дефолт если нет."""
        if self.subjects is None:
            self.subjects = default_subjects()
        if subject not in self.subjects:
            self.subjects[subject] = {"level": 1, "streak": 0, "wrong_streak": 0, "points": 0}
        return self.subjects[subject]

    def get_level(self, subject: str) -> int:
        return self.subject_state(subject)["level"]

    def get_streak(self, subject: str) -> int:
        return self.subject_state(subject)["streak"]

    def get_wrong_streak(self, subject: str) -> int:
        return self.subject_state(subject)["wrong_streak"]

    def get_subject_points(self, subject: str) -> int:
        return self.subject_state(subject)["points"]


class Session(Base):
    __tablename__ = "sessions"

    id:       Mapped[int] = mapped_column(Integer, primary_key=True)
    child_id: Mapped[int] = mapped_column(ForeignKey("children.id"))

    # Предмет и тема
    subject:  Mapped[str] = mapped_column(String(20), default="математика")
    topic:    Mapped[str] = mapped_column(String(50))

    # Вопрос
    question: Mapped[str] = mapped_column(String(500))

    # Числовые ответы (математика)
    correct_answer: Mapped[int] = mapped_column(Integer, default=0)
    user_answer:    Mapped[int] = mapped_column(Integer, default=0)

    # Текстовые ответы (русский, чтение)
    correct_text: Mapped[str] = mapped_column(String(200), default="")
    user_text:    Mapped[str] = mapped_column(String(200), default="")

    is_correct:    Mapped[bool] = mapped_column(Boolean)
    points_earned: Mapped[int]  = mapped_column(Integer, default=0)
    created_at:    Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    child: Mapped["Child"] = relationship(back_populates="sessions")


class RewardRequest(Base):
    __tablename__ = "reward_requests"

    id:           Mapped[int]      = mapped_column(Integer, primary_key=True)
    child_id:     Mapped[int]      = mapped_column(ForeignKey("children.id"))
    reward_name:  Mapped[str]      = mapped_column(String(100))
    reward_emoji: Mapped[str]      = mapped_column(String(10))
    points_cost:  Mapped[int]      = mapped_column(Integer)
    status:       Mapped[str]      = mapped_column(String(20), default="pending")
    created_at:   Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    child: Mapped["Child"] = relationship(back_populates="rewards")