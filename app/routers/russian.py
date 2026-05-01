import json
from fastapi import APIRouter, Request, Depends
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.services.russian.tasks import (
    generate_russian_task, explain_russian_mistake, LEVEL_CONFIG
)
from app.services.child_service import get_or_create_child, save_answer

router = APIRouter(prefix="/russian", tags=["russian"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/select")
async def select_topic(
    request: Request,
    child_name: str,
    db: AsyncSession = Depends(get_db),
):
    child      = await get_or_create_child(db, child_name)
    level      = child.get_level("русский")
    level_info = LEVEL_CONFIG.get(level, LEVEL_CONFIG[1])
    return templates.TemplateResponse(request, "russian/select.html", {
        "child":      child,
        "level_info": level_info,
        "level":      level,
    })


@router.get("/task")
async def get_task(
    request: Request,
    topic:      str = "всё",
    child_name: str = "Ребёнок",
    db: AsyncSession = Depends(get_db),
):
    child = await get_or_create_child(db, child_name)
    level = child.get_level("русский")
    task  = await generate_russian_task(topic, level)

    return templates.TemplateResponse(request, "russian/task.html", {
        "task":         task,
        "topic":        topic,
        "child":        child,
        "subject":      "русский",
        "level":        level,
        "task_json":    json.dumps(task, ensure_ascii=False),
        "level_config": LEVEL_CONFIG.get(level, LEVEL_CONFIG[1]),
    })


@router.post("/check")
async def check_answer(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    form          = await request.form()
    user_answer   = form.get("answer", "").strip()
    correct       = form.get("correct", "").strip()
    topic         = form.get("topic", "всё")
    child_name    = form.get("child_name", "Ребёнок")
    task_json_str = form.get("task_json", "{}")

    try:
        task = json.loads(task_json_str)
    except Exception:
        task = {}

    child      = await get_or_create_child(db, child_name)
    is_correct = user_answer.lower() == correct.lower()

    explanation = None
    if not is_correct:
        explanation = await explain_russian_mistake(task, user_answer)

    child, leveled_up = await save_answer(
        db, child,
        subject      = "русский",
        topic        = topic,
        question     = task.get("question", ""),
        is_correct   = is_correct,
        correct_text = correct,
        user_text    = user_answer,
    )

    return templates.TemplateResponse(request, "russian/feedback.html", {
        "is_correct":  is_correct,
        "explanation": explanation,
        "correct":     correct,
        "user_answer": user_answer,
        "child":       child,
        "subject":     "русский",
        "topic":       topic,
        "leveled_up":  leveled_up,
        "hint":        task.get("hint", ""),
    })