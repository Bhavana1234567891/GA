from fastapi import APIRouter, HTTPException

from models.book import Book

from services.book_service import (
    fetch_books,
    create_book
)

router = APIRouter()

@router.get("/books")
def get_books():
    return fetch_books()


@router.post("/books")
def add_new_book(book: Book):

    try:
        return create_book(book)

    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )