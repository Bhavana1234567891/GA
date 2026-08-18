from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(
    title="Library API",
    description="API for managing books in a library",
    version="1.0"
)

class Book(BaseModel):
    title: str
    author: str
    price: float

books = []

@app.get("/library", summary="Get all books")
def get_books():
    return books

@app.post("/books", summary="Add a new book")
def add_book(book: Book):
    books.append(book)
    return book



'''step 1: pip install fastapi uvicorn
step 2: create main.py
step 3: run      python -m uvicorn main:app --reload
step 4: open  http://127.0.0.1:8000/docs'''








