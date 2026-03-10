from sqlalchemy.future import select
from app.models import Book
from app.schemas import BookResponse


async def create_book(db, book):
    new_book = Book(**book.dict())

    db.add(new_book)
    await db.commit()
    await db.refresh(new_book)

    return new_book


async def get_books(db):
    result = await db.execute(select(Book))
    return result.scalars().all()


async def update_book(db, book_id, book_data):
    result = await db.execute(select(Book).where(Book.id == book_id))
    book = result.scalar_one_or_none()

    if not book:
        return None

    book.title = book_data.title
    book.author = book_data.author
    book.isbn = book_data.isbn
    book.valuation_rate = book_data.valuation_rate
    # book.status = book_data.status

    await db.commit()
    await db.refresh(book)

    return book


async def delete_book(db, book_id):
    result = await db.execute(select(Book).where(Book.id == book_id))
    book = result.scalar_one_or_none()

    if not book:
        return None

    await db.delete(book)
    await db.commit()

    return {"message": "Book deleted successfully"}