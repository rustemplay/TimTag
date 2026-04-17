"""
app/services/math/tasks.py
Генератор задач по математике (бывший ai_client.py).
Импорт в роутере: from app.services.math.tasks import generate_math_task, explain_mistake, LEVEL_CONFIG
"""
import json
import random
from app.services.ai_provider import chat

EMOJIS = ["🍎", "🐦", "🐟", "🌸", "🚗", "📚", "🍊", "⭐", "🐶", "🎈", "🍕", "🐱", "🏀", "🍓", "🦋"]

LEVEL_CONFIG = {
    1: {"bounds": (1, 9),   "task_types": ["simple"],                                           "description": "числа до 10"},
    2: {"bounds": (1, 19),  "task_types": ["simple", "missing"],                                "description": "числа до 20, найди ?"},
    3: {"bounds": (5, 49),  "task_types": ["simple", "missing", "compare"],                     "description": "числа до 50, вычисли выражение"},
    4: {"bounds": (5, 99),  "task_types": ["simple", "missing", "compare", "chain3"],           "description": "числа до 100, цепочки из 3"},
    5: {"bounds": (10, 99), "task_types": ["simple", "missing", "compare", "chain3", "chain5"], "description": "всё вперемешку"},
}


# ──────────────────────────────────────────
# ГЕНЕРАТОРЫ ЗАДАЧ (локально, без AI)
# ──────────────────────────────────────────

def _rand(lo, hi):
    return random.randint(lo, hi)


def make_simple(bounds, topic):
    lo, hi = bounds
    a, b = _rand(lo, hi), _rand(lo, hi)
    emoji = random.choice(EMOJIS)
    if topic == "вычитание":
        a, b = max(a, b), min(a, b)
        if a == b:
            b = max(lo, a - _rand(1, 3))
        return {"question": f"Было {a} {emoji}. Ушли {b}. Сколько осталось?", "answer": a - b, "type": "simple"}
    return {"question": f"В корзине {a} {emoji} и ещё {b} {emoji}. Сколько всего?", "answer": a + b, "type": "simple"}


def make_missing(bounds, topic):
    lo, hi = bounds
    a, b = _rand(lo, hi), _rand(lo, hi)
    if topic == "вычитание":
        a, b = max(a, b), min(a, b)
        if a == b:
            b = max(lo, a - 1)
        r = a - b
        if random.random() > 0.5:
            return {"question": f"? − {b} = {r}", "answer": a, "type": "missing"}
        return {"question": f"{a} − ? = {r}", "answer": b, "type": "missing"}
    r = a + b
    if random.random() > 0.5:
        return {"question": f"? + {b} = {r}", "answer": a, "type": "missing"}
    return {"question": f"{a} + ? = {r}", "answer": b, "type": "missing"}


def make_compare(bounds):
    lo, hi = bounds
    a, b = _rand(lo, hi), _rand(lo, hi)
    op = random.choice(["+", "-"])
    if op == "-":
        a, b = max(a, b), min(a, b)
        if a == b:
            b = max(lo, a - 1)
        answer = a - b
    else:
        answer = a + b
    return {"question": f"Вычисли: {a} {op} {b} = ?", "answer": answer, "type": "compare"}


def make_chain(bounds, length):
    lo, hi = bounds
    current = _rand(lo, min(hi, 20))
    nums, ops = [current], []
    for _ in range(length - 1):
        op = random.choice(["+", "-"])
        if op == "-":
            b = _rand(1, max(1, current - 1)) if current > 1 else 1
            if current <= 1:
                op, b = "+", _rand(1, min(10, hi - current))
        else:
            b = _rand(1, min(10, hi - current)) if current < hi else 1
        ops.append(op)
        nums.append(b)
        current = current + b if op == "+" else current - b
    expr = str(nums[0]) + "".join(f" {ops[i]} {nums[i+1]}" for i in range(len(ops)))
    return {"question": f"{expr} = ?", "answer": current, "type": f"chain{length}"}


# ──────────────────────────────────────────
# ГЛАВНАЯ ФУНКЦИЯ
# ──────────────────────────────────────────

async def generate_math_task(topic: str, level: int) -> dict:
    if topic == "арифметика":
        topic = random.choice(["сложение", "вычитание"])

    cfg = LEVEL_CONFIG.get(level, LEVEL_CONFIG[1])
    task_type = random.choice(cfg["task_types"])

    generators = {
        "simple":  lambda: make_simple(cfg["bounds"], topic),
        "missing": lambda: make_missing(cfg["bounds"], topic),
        "compare": lambda: make_compare(cfg["bounds"]),
        "chain3":  lambda: make_chain(cfg["bounds"], 3),
        "chain5":  lambda: make_chain(cfg["bounds"], 5),
    }
    task = generators.get(task_type, generators["simple"])()

    # Уровни 3+ — украшаем простые задачи живым текстом через AI
    if task_type == "simple" and level >= 3:
        task = await _enrich_with_ai(task, topic)

    return task


async def _enrich_with_ai(task, topic):
    q = task["question"]
    if topic == "вычитание":
        action    = "вычитание (убрали/ушли/съели)"
        forbidden = "НЕ используй: дали, добавили"
    else:
        action    = "сложение (добавили/пришли/нашли)"
        forbidden = "НЕ используй: убрали, ушли, съели"

    prompt = (
        f"Перепиши задачу для ребёнка 8 лет. Сохрани числа.\n"
        f"Исходная: {q}\n"
        f"Тема: {action}. {forbidden}.\n"
        f"Максимум 12 слов, 1 эмодзи.\n"
        f'Ответь строго в JSON: {{"question": "текст"}}'
    )
    try:
        text = await chat(prompt, temperature=0.7, json_mode=True)
        task["question"] = json.loads(text).get("question", q)
    except Exception:
        pass  # fallback — оставляем оригинальный текст
    return task


async def explain_mistake(question: str, user_answer: int, correct_answer: int) -> str:
    prompt = (
        f"Ты помощник для ребёнка 7-9 лет. Ребёнок ОШИБСЯ.\n"
        f"Задача: {question}\n"
        f"Ответил неправильно: {user_answer}. Правильный ответ: {correct_answer}.\n"
        f"Объясни в 2 предложения почему ответ {correct_answer}. "
        f"Начни с 'Давай разберём вместе 🤔'. Не говори что он прав."
    )
    try:
        return await chat(prompt, temperature=0.3)
    except Exception:
        return f"Давай разберём вместе 🤔 Правильный ответ — {correct_answer}. Попробуй ещё раз! 💪"