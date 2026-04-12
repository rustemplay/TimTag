from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select
from app.routers import math, child, rewards
from app.database import engine, Base, AsyncSession
from app.models.models import Child
from app import models

app = FastAPI(title="TimTag", debug=True)
templates = Jinja2Templates(directory="app/templates")
app.mount("/static", StaticFiles(directory="app/static"), name="static")
app.include_router(math.router)
app.include_router(child.router)
app.include_router(rewards.router)


@app.on_event("startup")
async def startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


@app.get("/")
async def root(request: Request):
    async with AsyncSession() as db:
        result = await db.execute(select(Child).order_by(Child.name))
        children = result.scalars().all()
    return templates.TemplateResponse(request, "index.html", {
        "children": children,
    })