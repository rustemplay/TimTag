from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from app.models.models import Child, Session, RewardRequest

MAX_LEVEL = 5
STREAK_TO_LEVELUP = 8   # серия правильных → повышение уровня
ERRORS_TO_LEVELDOWN = 3  # серия ошибок подряд → понижение уровня

# Очки за правильный ответ по уровням
POINTS_PER_LEVEL = {1: 0, 2: 1, 3: 1, 4: 2, 5: 3}

REWARDS = [
    {"name": "Телевизор",      "emoji": "📺", "cost": 100},
    {"name": "Телефон",        "emoji": "📱", "cost": 150},
    {"name": "Время с мамой",  "emoji": "👩", "cost": 120},
    {"name": "Время с папой",  "emoji": "👨", "cost": 120},
    {"name": "Мороженое",      "emoji": "🍦", "cost": 130},
    {"name": "Прогулка",       "emoji": "🚴", "cost": 50},
]


async def get_or_create_child(db: AsyncSession, name: str) -> Child:
    result = await db.execute(select(Child).where(Child.name == name))
    child = result.scalar_one_or_none()
    if not child:
        child = Child(name=name)
        db.add(child)
        await db.commit()
        await db.refresh(child)
    return child


async def save_answer(
    db: AsyncSession,
    child: Child,
    topic: str,
    question: str,
    correct_answer: int,
    user_answer: int,
    is_correct: bool,
) -> Child:
    # Очки по уровням: 0 / 1 / 1 / 2 / 3
    points_earned = POINTS_PER_LEVEL.get(child.level, 0) if is_correct else 0

    session = Session(
        child_id=child.id,
        topic=topic,
        question=question,
        correct_answer=correct_answer,
        user_answer=user_answer,
        is_correct=is_correct,
        points_earned=points_earned,
    )
    db.add(session)

    if is_correct:
        child.points += points_earned
        child.streak += 1
        # wrong_streak НЕ сбрасываем — копится независимо

        # Повышение уровня — серия из 8 правильных подряд
        if child.streak >= STREAK_TO_LEVELUP and child.level < MAX_LEVEL:
            child.level += 1
            child.streak = 0
            child.wrong_streak = 0
    else:
        child.wrong_streak += 1

        # Понижение уровня — 3 ошибки подряд (не ниже 1)
        if child.wrong_streak >= ERRORS_TO_LEVELDOWN and child.level > 1:
            child.level -= 1
            child.streak = 0
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
    total = await db.execute(
        select(func.count(Session.id)).where(Session.child_id == child_id)
    )
    total = total.scalar() or 0

    correct = await db.execute(
        select(func.count(Session.id)).where(
            Session.child_id == child_id,
            Session.is_correct == True
        )
    )
    correct = correct.scalar() or 0

    recent = await db.execute(
        select(Session)
        .where(Session.child_id == child_id)
        .order_by(desc(Session.created_at))
        .limit(10)
    )
    recent = recent.scalars().all()

    weak = await db.execute(
        select(Session.topic, func.count(Session.id).label("errors"))
        .where(Session.child_id == child_id, Session.is_correct == False)
        .group_by(Session.topic)
        .order_by(desc("errors"))
    )
    weak = weak.all()

    pending_rewards = await db.execute(
        select(RewardRequest)
        .where(
            RewardRequest.child_id == child_id,
            RewardRequest.status == "pending"
        )
        .order_by(desc(RewardRequest.created_at))
    )
    pending_rewards = pending_rewards.scalars().all()

    accuracy = round((correct / total * 100)) if total > 0 else 0

    return {
        "total": total,
        "correct": correct,
        "wrong": total - correct,
        "accuracy": accuracy,
        "recent": recent,
        "weak_topics": weak,
        "pending_rewards": pending_rewards,
    }