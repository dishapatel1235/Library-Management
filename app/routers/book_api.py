from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from fastapi.templating import Jinja2Templates

from app.database import get_db
from app.services import book_service, transaction_service, member_service
from app.schemas import BookCreate, BookUpdate
from app.models.books import BookStatus
from datetime import datetime, timezone

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


# DASHBOARD
@router.get("/", response_class=HTMLResponse)
async def dashboard_page(request: Request, db: AsyncSession = Depends(get_db)):
    books = await book_service.get_books(db)
    return templates.TemplateResponse(
        "dashboard.html",
        {"request": request, "books": books}
    )

@router.get("/api/dashboard/stats")
async def dashboard_stats(db: AsyncSession = Depends(get_db)):
    members = await member_service.get_members(db)
    total_members = len(members)

    transactions = await transaction_service.get_all_transactions(db)
    total_transactions = len(transactions)
    
    total_fine = 0
    now = datetime.now(timezone.utc)

    for txn in transactions:
        issued_books_count = 0
        for b in txn["books"]:
            status_obj = b.get("status") if isinstance(b, dict) else getattr(b, "status", None)
            status_val = status_obj.value if hasattr(status_obj, "value") else str(status_obj)
            if status_val.lower() == "issued":
                issued_books_count += 1
                
        if issued_books_count > 0 and txn["due_date"]:
            due_time = txn["due_date"].replace(tzinfo=timezone.utc) if txn["due_date"].tzinfo is None else txn["due_date"]
            if due_time < now:
                days_overdue = (now.date() - due_time.date()).days
                if days_overdue > 0:
                    total_fine += days_overdue * 2 * issued_books_count
    
    books = await book_service.get_books(db)
    total_books = len(books)
    
    borrowed_books = sum(1 for b in books if (b.status.value.lower() == "issued" if hasattr(b.status, "value") else str(b.status).lower() == "issued"))

    return {
        "total_books": total_books,
        "borrowed_books": borrowed_books,
        "total_transactions": total_transactions,
        "total_members": total_members,
        "total_fine": total_fine
    }

@router.get("/api/dashboard/overdue")
async def dashboard_overdue(db: AsyncSession = Depends(get_db)):
    transactions = await transaction_service.get_all_transactions(db)
    now = datetime.now(timezone.utc)
    overdue_txns = []

    for txn in transactions:
        if txn["due_date"]:
            due_time = txn["due_date"].replace(tzinfo=timezone.utc) if txn["due_date"].tzinfo is None else txn["due_date"]
            if due_time < now:
                has_issued = any(b["status"].value.lower() == "issued" if hasattr(b["status"], "value") else str(b["status"]).lower() == "issued" for b in txn["books"])
                if has_issued:
                    due_date_str = txn["due_date"].strftime('%Y-%m-%dT%H:%M:%S')
                    books_title = ", ".join([b["title"] for b in txn["books"]])
                    overdue_txns.append({
                        "id": txn["id"],
                        "member_name": txn["member_name"],
                        "books_title": books_title,
                        "due_date": due_date_str
                    })

    return overdue_txns

# LIST BOOKS
@router.get("/books", response_class=HTMLResponse)
async def books_page(request: Request, db: AsyncSession = Depends(get_db)):

    books = await book_service.get_books(db)

    return templates.TemplateResponse(
        "books.html",
        {"request": request, "books": books}
    )


# ADD BOOK FORM
@router.get("/books/add", response_class=HTMLResponse)
async def add_book_page(request: Request):

    return templates.TemplateResponse(
        "book_form.html",
        {"request": request}
    )


# CREATE BOOK
@router.post("/books/add")
async def create_book(
    request: Request,
    title: str = Form(...),
    author: str = Form(...),
    isbn: str = Form(...),
    valuation_rate: int = Form(...),
    db: AsyncSession = Depends(get_db)
):
    try:
        book = BookCreate(
            title=title,
            author=author,
            isbn=isbn,
            valuation_rate=valuation_rate
        )

        await book_service.create_book(db, book)
        return RedirectResponse("/books", status_code=303)
        
    except IntegrityError:
        return templates.TemplateResponse(
            "book_form.html",
            {
                "request": request,
                "error": "Database Error: A book with this ISBN already exists."
            }
        )
    except Exception as e:
        return templates.TemplateResponse(
            "book_form.html",
            {
                "request": request,
                "error": str(e.detail) if hasattr(e, 'detail') else str(e)
            }
        )

# EDIT BOOK FORM
@router.get("/books/edit/{book_id}", response_class=HTMLResponse)
async def edit_book_page(
    request: Request,
    book_id: int,
    db: AsyncSession = Depends(get_db)
):

    books = await book_service.get_books(db)
    book = next((b for b in books if b.id == book_id), None)

    if not book:
        return RedirectResponse("/books", status_code=303)

    return templates.TemplateResponse(
        "book_form.html",
        {
            "request": request,
            "book": book
        }
    )


# UPDATE BOOK
@router.post("/books/update/{book_id}")
async def update_book(
    request: Request,
    book_id: int,
    title: str = Form(...),
    author: str = Form(...),
    isbn: str = Form(...),
    valuation_rate: int = Form(...),
    db: AsyncSession = Depends(get_db)
):
    try:
        book_update = BookUpdate(
            title=title,
            author=author,
            isbn=isbn,
            valuation_rate=valuation_rate
        )

        await book_service.update_book(db, book_id, book_update)
        return RedirectResponse("/books", status_code=303)
        
    except IntegrityError:
        books = await book_service.get_books(db)
        book = next((b for b in books if b.id == book_id), None)
        return templates.TemplateResponse(
            "book_form.html",
            {
                "request": request,
                "book": book,
                "error": "Database Error: A book with this ISBN already exists."
            }
        )
    except Exception as e:
        books = await book_service.get_books(db)
        book = next((b for b in books if b.id == book_id), None)
        return templates.TemplateResponse(
            "book_form.html",
            {
                "request": request,
                "book": book,
                "error": str(e.detail) if hasattr(e, 'detail') else str(e)
            }
        )

# DELETE BOOK
@router.get("/books/delete/{book_id}")
async def delete_book(book_id: int, db: AsyncSession = Depends(get_db)):

    await book_service.delete_book(db, book_id)

    return RedirectResponse("/books", status_code=303)


# router = APIRouter()
# templates = Jinja2Templates(directory="app/templates")

# @router.post("/create_books", response_model=BookResponse)
# async def create_book(book: BookCreate, db: AsyncSession = Depends(get_db)):
#     return await book_service.create_book(db, book)

# @router.get("/list_books", response_model=List[BookResponse])
# async def list_books(db: AsyncSession = Depends(get_db)):
#     return await book_service.get_books(db)

# @router.put("/update_book/{book_id}", response_model=BookResponse)
# async def update_book(book_id: int, book: BookUpdate, db: AsyncSession = Depends(get_db)):
#     updated_book = await book_service.update_book(db, book_id, book)

#     if not updated_book:
#         raise HTTPException(status_code=404, detail="Book not found")

#     return updated_book


# @router.delete("/delete_book/{book_id}")
# async def delete_book(book_id: int, db: AsyncSession = Depends(get_db)):
#     deleted_book = await book_service.delete_book(db, book_id)

#     if not deleted_book:
#         raise HTTPException(status_code=404, detail="Book not found")

#     return deleted_book
