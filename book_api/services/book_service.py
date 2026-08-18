from repositories.book_repository import (
    get_all_books,
    add_book
)

def fetch_books():
    return get_all_books()

def create_book(book):
    if len(book.title) < 3:
        raise ValueError(
            "Book title must have at least 3 characters."
        )
    return add_book(book)