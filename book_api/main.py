from fastapi import FastAPI
from api.book_api import router

app = FastAPI()

app.include_router(router)