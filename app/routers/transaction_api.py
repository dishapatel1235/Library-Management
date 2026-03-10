from datetime import datetime, timedelta
from enum import member

from fastapi import APIRouter, Depends, HTTPException, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.database import get_db
from app.models.transaction import TransactionType
from app.schemas import TransactionCreate, TransactionResponse, TransactionUpdateRequest
from app.schemas.transaction_schema import TransactionUpdateRequestItem
from app.services import transaction_service, member_service, book_service

router = APIRouter()

templates = Jinja2Templates(directory="app/templates")


# LIST TRANSACTIONS PAGE
@router.get("/transactions", response_class=HTMLResponse)
async def transactions_page(request: Request, db: AsyncSession = Depends(get_db)):

    transactions = await transaction_service.get_all_transactions(db)

    return templates.TemplateResponse(
        "transactions.html",
        {
            "request": request,
            "transactions": transactions
        }
    )


# CREATE TRANSACTION FORM PAGE
@router.get("/transactions/add", response_class=HTMLResponse)
async def add_transaction_page(
    request: Request,
    db: AsyncSession = Depends(get_db)
):

    members = await member_service.get_members(db)
    books = await book_service.get_books(db)

    return templates.TemplateResponse(
        "transaction_form.html",
        {
            "request": request,
            "members": members,
            "books": books
        }
    )


# CREATE TRANSACTION (FORM SUBMIT)

@router.post("/transactions/add")
async def create_transaction_ui(
    request: Request,
    member_id: int = Form(...),
    book_ids: List[int] = Form(...),
    db: AsyncSession = Depends(get_db)
):
    try:
        books = [{"book_id": b} for b in book_ids]

        data = TransactionCreate(
            member_id=member_id,
            books=books,
            due_date=datetime.utcnow() + timedelta(days=14),  # default 14 day loan
            transaction_type=TransactionType.ISSUE
        )

        await transaction_service.create_transaction(db, data)
        return RedirectResponse("/transactions", status_code=303)
        
    except Exception as e:
        members = await member_service.get_members(db)
        books_list = await book_service.get_books(db)
        return templates.TemplateResponse(
            "transaction_form.html",
            {
                "request": request,
                "members": members,
                "books": books_list,
                "error": str(e.detail) if hasattr(e, 'detail') else str(e)
            }
        )

@router.post("/create_transaction")
async def create_transaction(data: TransactionCreate, db: AsyncSession = Depends(get_db)):
    return await transaction_service.create_transaction(db, data)


@router.get("/list_transactions", response_model=List[TransactionResponse])
async def list_transactions(db: AsyncSession = Depends(get_db)):
    return await transaction_service.get_all_transactions(db)


@router.put("/transaction/mixed/{transaction_id}")
async def update_transaction_mixed(
    transaction_id: int,
    request: TransactionUpdateRequest,
    db: AsyncSession = Depends(get_db)
):
    try:
        txn = await transaction_service.update_transaction_mixed(
            db,
            transaction_id,
            [book.dict() for book in request.books]
        )

        return {
            "transaction_id": txn.id,
            "due_date": txn.due_date,
            "books": [
                {
                    "id": book.id,
                    "title": book.title,
                    "status": book.status.value
                }
                for book in txn.books
            ]
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/transaction/{transaction_id}")
async def delete_transaction(transaction_id: int, db: AsyncSession = Depends(get_db)):
    try:
        return await transaction_service.delete_transaction(db, transaction_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    
# @router.get("/transactions/edit/{transaction_id}", response_class=HTMLResponse)
# async def edit_transaction_page(
#     transaction_id: int,
#     request: Request,
#     db: AsyncSession = Depends(get_db)
# ):
#     txn = await transaction_service.get_transaction_by_id(db, transaction_id)

#     members = await member_service.get_members(db)
#     books = await book_service.get_books(db)

#     return templates.TemplateResponse(
#         "transaction_edit.html",
#         {
#             "request": request,
#             "transaction": txn,
#             "members": members,
#             "books": books
#         }
#     )

@router.get("/transactions/edit/{transaction_id}", response_class=HTMLResponse)
async def edit_transaction_page(
    transaction_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    txn = await transaction_service.get_transaction_by_id(db, transaction_id)
    members = await member_service.get_members(db)  # optional, could skip if member is fixed
    books = await book_service.get_books(db)        # optional, template uses txn.books
    return templates.TemplateResponse(
        "transaction_edit.html",
        {
            "request": request,
            "transaction": txn,
            "members": members,
            "books": books
        }
    )

@router.post("/transactions/edit/{transaction_id}")
async def update_transaction_ui(
    request: Request,
    transaction_id: int,
    book_ids: List[int] = Form(...),
    transaction_types: List[str] = Form(...),
    due_date: str = Form(None),
    db: AsyncSession = Depends(get_db)
):
    try:
        if len(book_ids) != len(transaction_types):
            raise Exception("Books and statuses mismatch")

        parsed_due_date = None
        if due_date:
            try:
                if 'T' in due_date:
                    parsed_due_date = datetime.strptime(due_date, '%Y-%m-%dT%H:%M')
                else:
                    parsed_due_date = datetime.strptime(due_date, '%Y-%m-%d')
            except ValueError:
                pass

        # Convert to Pydantic objects
        books = [
            TransactionUpdateRequestItem(
                book_id=book_ids[i],
                transaction_type=transaction_types[i]
            )
            for i in range(len(book_ids))
        ]

        # Call your service
        await transaction_service.update_transaction_mixed(db, transaction_id, books, due_date=parsed_due_date)

        return RedirectResponse("/transactions", status_code=303)
        
    except Exception as e:
        txn = await transaction_service.get_transaction_by_id(db, transaction_id)
        members = await member_service.get_members(db)
        books_list = await book_service.get_books(db)
        return templates.TemplateResponse(
            "transaction_edit.html",
            {
                "request": request,
                "transaction": txn,
                "members": members,
                "books": books_list,
                "error": str(e.detail) if hasattr(e, 'detail') else str(e)
            }
        )



# DELETE TRANSACTION
@router.get("/transactions/delete/{transaction_id}")
async def delete_transaction_ui(
    transaction_id: int,
    db: AsyncSession = Depends(get_db)
):

    await transaction_service.delete_transaction(db, transaction_id)

    return RedirectResponse(url="/transactions", status_code=303)


# @router.post("/create_transaction")
# async def create_transaction(data: TransactionCreate, db: AsyncSession = Depends(get_db)):
#     return await transaction_service.create_transaction(db, data)


# @router.get("/list_transactions", response_model=list[TransactionResponse])
# async def list_transactions(db: AsyncSession = Depends(get_db)):
#     """
#     Get all transactions with member and book details.
#     """
#     transactions = await transaction_service.get_all_transactions(db)
#     return transactions


# @router.put("/transaction/mixed/{transaction_id}")
# async def update_transaction_mixed(
#     transaction_id: int,
#     request: TransactionUpdateRequest,
#     db: AsyncSession = Depends(get_db)
# ):
#     """
#     Update multiple books in a transaction with mixed operations.
#     """
#     try:
#         txn = await transaction_service.update_transaction_mixed(
#             db, transaction_id, [book.dict() for book in request.books]
#         )
#         return {
#             "transaction_id": txn.id,
#             "due_date": txn.due_date,
#             "books": [
#                 {"id": book.id, "title": book.title, "status": book.status.value} 
#                 for book in txn.books
#             ]
#         }
#     except Exception as e:
#         raise HTTPException(status_code=400, detail=str(e))


# @router.delete("/transaction/{transaction_id}")
# async def delete_transaction(transaction_id: int, db: AsyncSession = Depends(get_db)):
#     try:
#         result = await transaction_service.delete_transaction(db, transaction_id)
#         return result
#     except Exception as e:
#         raise HTTPException(status_code=400, detail=str(e))
    

    