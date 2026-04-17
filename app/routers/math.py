from fastapi import APIRouter, Request, Depends
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.services.math.tasks import generate_math_task, explain_mistake, LEVEL_CONFIG
from app.services.child_service import get_or_create_child, save_answer

router = APIRouter(prefix="/math", tags=["math"])
templates = Jinja2Templates(directory="app/templates")


def get_max_answer(level: int) -> int:
    bounds = LEVEL_CONFIG.get(level, LEVEL_CONFIG[1])["bounds"]
    lo, hi = bounds
    return hi * 2


@router.get("/task")
async def get_task(
    request: Request,
    topic: str = "сложение",
    child_name: str = "Ребёнок",
    db: AsyncSession = Depends(get_db),
):
    child = await get_or_create_child(db, child_name)
    task = await generate_math_task(topic, child.level)
    max_answer = get_max_answer(child.level)

    return templates.TemplateResponse(request, "math/task.html", {
        "task": task,
        "topic": topic,
        "child": child,
        "max_answer": max_answer,
        "level_config": LEVEL_CONFIG.get(child.level, LEVEL_CONFIG[1]),
    })


@router.post("/check")
async def check_answer(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    form = await request.form()
    user_answer   = int(form.get("answer"))
    correct_answer = int(form.get("correct"))
    question   = form.get("question")
    topic      = form.get("topic")
    child_name = form.get("child_name")

    child = await get_or_create_child(db, child_name)
    is_correct = user_answer == correct_answer

    explanation = None
    if not is_correct:
        explanation = await explain_mistake(question, user_answer, correct_answer)

    child = await save_answer(
        db, child, "математика", topic, question,
        correct_answer, user_answer, is_correct
    )

    leveled_up = is_correct and child.streak == 0 and child.level > 1

    return templates.TemplateResponse(request, "math/feedback.html", {
        "is_correct":   is_correct,
        "explanation":  explanation,
        "correct":      correct_answer,
        "child":        child,
        "topic":        topic,
        "leveled_up":   leveled_up,
    })


@router.get("/select")
async def select_topic(
    request: Request,
    child_name: str,
    db: AsyncSession = Depends(get_db),
):
    child = await get_or_create_child(db, child_name)
    level_info = LEVEL_CONFIG.get(child.level, LEVEL_CONFIG[1])
    return templates.TemplateResponse(request, "math/select.html", {
        "child":      child,
        "level_info": level_info,
    })