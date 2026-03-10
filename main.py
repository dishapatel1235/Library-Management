from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from app.routers.book_api import router as book_router
from app.routers.member_api import router as member_router
from app.routers.transaction_api import router as transaction_router

app = FastAPI()
templates = Jinja2Templates(directory="app/templates")

# app.mount("/static", StaticFiles(directory="app/static"), name="static")
app.include_router(book_router)
app.include_router(member_router)
app.include_router(transaction_router)