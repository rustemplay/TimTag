from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from app.models.models import Child, Session, RewardRequest

MAX_LEVEL = 5
STREAK_TO_LEVELUP   = 8
ERRORS_TO_LEVELDOWN = 3

POINTS_PER_LEVEL = {1: 0, 2: 1, 3: 1, 4: 2, 5: 3}

REWARDS = [
    {"name": "Телевизор",     "emoji": "📺", "cost": 100},
    {"name": "Телефон",       "emoji": "📱", "cost": 150},
    {"name": "Время с мамой", "emoji": "👩", "cost": 120},
    {"name": "Время с папой", "emoji": "👨", "cost": 120},
    {"name": "Мороженое",     "emoji": "🍦", "cost": 130},
    {"name": "Прогулка",      "emoji": "🚴", "cost": 50},
]


async def get_or_create_child(db: AsyncSession, name: str) -> Child:
    result = await db.execute(select(Child).where(Child.name == name))
    child  = result.scalar_one_or_none()
    if not child:
        child = Child(name=name)
        db.add(child)
        await db.commit()
        await db.refresh(child)
    return child


async def save_answer(
    db: AsyncSession,
    child: Child,
    subject: str,           # "математика" / "русский" / "чтение"
    topic: str,
    question: str,
    correct_answer: int,
    user_answer: int,
    is_correct: bool,
    correct_text: str = "", # для текстовых ответов (русский, чтение)
    user_text: str = "",
) -> Child:
    points_earned = POINTS_PER_LEVEL.get(child.level, 0) if is_correct else 0

    session = Session(
        child_id=child.id,
        subject=subject,
        topic=topic,
        question=question,
        correct_answer=correct_answer,
        user_answer=user_answer,
        correct_text=correct_text,
        user_text=user_text,
        is_correct=is_correct,
        points_earned=points_earned,
    )
    db.add(session)

    if is_correct:
        child.points += points_earned
        child.streak += 1
        if child.streak >= STREAK_TO_LEVELUP and child.level < MAX_LEVEL:
            child.level       += 1
            child.streak       = 0
            child.wrong_streak = 0
    else:
        child.wrong_streak += 1
        if child.wrong_streak >= ERRORS_TO_LEVELDOWN and child.level > 1:
            child.level       -= 1
            child.streak       = 0
            child.wrong_streak = 0

    await db.commit()
    await db.refresh(child)
    return child


async def request_reward(
    db: AsyncSession,
    child: Child,
    reward_name: str,
    reward_emoji: str,
    points_cost: int,
) -> dict:
    if child.points < points_cost:
        return {"ok": False, "msg": "Недостаточно очков"}
    req = RewardRequest(
        child_id=child.id,
        reward_name=reward_name,
        reward_emoji=reward_emoji,
        points_cost=points_cost,
        status="pending",
    )
    db.add(req)
    child.points -= points_cost
    await db.commit()
    return {"ok": True}


async def approve_reward(db: AsyncSession, request_id: int) -> bool:
    result = await db.execute(
        select(RewardRequest).where(RewardRequest.id == request_id)
    )
    req = result.scalar_one_or_none()
    if not req:
        return False
    req.status = "approved"
    await db.commit()
    return True


async def get_child_stats(db: AsyncSession, child_id: int) -> dict:
    # ── Общая статистика ──────────────────────────────
    total = (await db.execute(
        select(func.count(Session.id)).where(Session.child_id == child_id)
    )).scalar() or 0

    correct = (await db.execute(
        select(func.count(Session.id)).where(
            Session.child_id == child_id,
            Session.is_correct == True,
        )
    )).scalar() or 0

    # ── Статистика по предметам ───────────────────────
    subjects_rows = (await db.execute(
        select(Session.subject, func.count(Session.id).label("total"))
        .where(Session.child_id == child_id)
        .group_by(Session.subject)
        .order_by(Session.subject)
    )).all()

    by_subject = []
    for row in subjects_rows:
        subj_correct = (await db.execute(
            select(func.count(Session.id)).where(
                Session.child_id == child_id,
                Session.subject  == row.subject,
                Session.is_correct == True,
            )
        )).scalar() or 0
        by_subject.append({
            "subject":  row.subject,
            "total":    row.total,
            "correct":  subj_correct,
            "accuracy": round(subj_correct / row.total * 100) if row.total else 0,
        })

    # ── Последние 10 ответов ──────────────────────────
    recent = (await db.execute(
        select(Session)
        .where(Session.child_id == child_id)
        .order_by(desc(Session.created_at))
        .limit(10)
    )).scalars().all()

    # ── Слабые темы (топ-5 по ошибкам) ───────────────
    weak = (await db.execute(
        select(
            Session.subject,
            Session.topic,
            func.count(Session.id).label("errors"),
        )
        .where(Session.child_id == child_id, Session.is_correct == False)
        .group_by(Session.subject, Session.topic)
        .order_by(desc("errors"))
        .limit(5)
    )).all()

    # ── Ожидающие награды ─────────────────────────────
    pending_rewards = (await db.execute(
        select(RewardRequest)
        .where(
            RewardRequest.child_id == child_id,
            RewardRequest.status   == "pending",
        )
        .order_by(desc(RewardRequest.created_at))
    )).scalars().all()

    accuracy = round(correct / total * 100) if total > 0 else 0

    return {
        "total":           total,
        "correct":         correct,
        "wrong":           total - correct,
        "accuracy":        accuracy,
        "by_subject":      by_subject,   # список dict по предметам
        "recent":          recent,
        "weak_topics":     weak,         # (subject, topic, errors)
        "pending_rewards": pending_rewards,
    }