from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models.models import Child
from app.services.child_service import (
    get_or_create_child, request_reward,
    approve_reward, REWARDS
)

router = APIRouter(prefix="/rewards", tags=["rewards"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/{child_id}")
async def rewards_page(
    request: Request,
    child_id: int,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Child).where(Child.id == child_id))
    child = result.scalar_one_or_none()
    if not child:
        return RedirectResponse(url="/")
    return templates.TemplateResponse(request, "rewards/index.html", {
        "child": child,
        "rewards": REWARDS,
    })


@router.post("/{child_id}/request")
async def request_reward_route(
    child_id: int,
    reward_name: str = Form(...),
    reward_emoji: str = Form(...),
    points_cost: int = Form(...),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Child).where(Child.id == child_id))
    child = result.scalar_one_or_none()
    await request_reward(db, child, reward_name, reward_emoji, points_cost)
    return RedirectResponse(url=f"/rewards/{child_id}", status_code=303)


@router.post("/approve/{request_id}")
async def approve(request_id: int, db: AsyncSession = Depends(get_db)):
    await approve_reward(db, request_id)
    return RedirectResponse(url="/", status_code=303)