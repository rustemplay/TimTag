from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.services.child_service import get_or_create_child, get_child_stats
from app.models.models import Child

router = APIRouter(prefix="/child", tags=["child"])
templates = Jinja2Templates(directory="app/templates")


@router.post("/create")
async def create_child(
    name: str = Form(...),
    db: AsyncSession = Depends(get_db),
):
    await get_or_create_child(db, name.strip())
    return RedirectResponse(url="/", status_code=303)


@router.get("/dashboard/{child_id}")
async def dashboard(
    request: Request,
    child_id: int,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Child).where(Child.id == child_id))
    child = result.scalar_one_or_none()
    if not child:
        return RedirectResponse(url="/")

    stats = await get_child_stats(db, child_id)
    return templates.TemplateResponse(request, "child/dashboard.html", {
        "child": child,
        "stats": stats,
    })