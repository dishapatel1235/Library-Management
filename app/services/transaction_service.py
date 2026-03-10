from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from app.models import Transaction, TransactionItem, Book, TransactionType, Member
from datetime import datetime, timezone, timedelta
from app.models.books import BookStatus
from app.models.members import MembershipType
from app.schemas.transaction_schema import TransactionUpdateRequestItem
from typing import List
from sqlalchemy import func

async def calculate_member_fines(db: AsyncSession, member_id: int):
    result = await db.execute(
        select(Transaction).where(Transaction.member_id == member_id).options(selectinload(Transaction.books))
    )
    transactions = result.scalars().all()

    now = datetime.now(timezone.utc)
    total_fine = 0

    for txn in transactions:
        if txn.due_date:
            txn_due_time = txn.due_date.replace(tzinfo=timezone.utc) if txn.due_date.tzinfo is None else txn.due_date
            if txn_due_time < now:
                days_overdue = (now.date() - txn_due_time.date()).days
                if days_overdue > 0:
                    issued_books_count = 0
                    for b in txn.books:
                        status_val = b.status.value if hasattr(b.status, "value") else str(b.status)
                        if status_val.lower() == "issued":
                            issued_books_count += 1
                    
                    if issued_books_count > 0:
                        total_fine += days_overdue * 2 * issued_books_count

    return total_fine


async def create_transaction(db: AsyncSession, transaction):
    due_date = transaction.due_date
    if due_date.tzinfo is None:
        due_date = due_date.replace(tzinfo=timezone.utc)

    posting_date = datetime.now(timezone.utc)

    # Fetch member
    member_query = await db.execute(
        select(Member).where(Member.id == transaction.member_id)
    )
    member = member_query.scalar_one_or_none()

    if not member:
        raise HTTPException(status_code=404, detail="Member not found")

    # Prevent duplicate books
    book_ids = [b.book_id for b in transaction.books]
    if len(book_ids) != len(set(book_ids)):
        raise HTTPException(status_code=400, detail="Duplicate books in request are not allowed")

    # Calculate unpaid fines
    unpaid_fines = await calculate_member_fines(db, member.id)
    
    # Calculate currently issued books per member
    member_txns_result = await db.execute(
        select(Transaction).where(Transaction.member_id == member.id).options(selectinload(Transaction.books))
    )
    member_txns = member_txns_result.scalars().all()
    
    issued_books_count = 0
    seen_books = set()
    for txn in member_txns:
        for b in txn.books:
            if b.id not in seen_books:
                seen_books.add(b.id)
                status_val = b.status.value if hasattr(b.status, "value") else str(b.status)
                if status_val.lower() == "issued":
                    issued_books_count += 1
    
    # Block transaction if member has > 3 books issued AND unpaid fines > 500
    if issued_books_count > 2 and unpaid_fines > 500:
        raise HTTPException(
            status_code=400,
            detail=f"Transaction blocked. Member has {issued_books_count} issued books and unpaid fines of ₹{unpaid_fines}"
        )

    member.total_unpaid_fines = unpaid_fines

    # Membership limits
    membership_limit = 2 if member.membership_type == MembershipType.Regular else 3

    # Validate before issuing
    if transaction.transaction_type == TransactionType.ISSUE:
        if len(transaction.books) > membership_limit:
            raise HTTPException(
                status_code=400,
                detail=f"{member.membership_type.value} members can issue only {membership_limit} books. "
                       f"You are trying to issue: {len(transaction.books)}"
            )

    # Create Transaction
    new_transaction = Transaction(
        member_id=member.id,
        posting_date=posting_date,
        due_date=due_date,
        transaction_type=transaction.transaction_type
    )

    db.add(new_transaction)
    await db.flush()

    books_response = []

    for item in transaction.books:
        book_query = await db.execute(select(Book).where(Book.id == item.book_id))
        book = book_query.scalar_one_or_none()

        if not book:
            raise HTTPException(status_code=404, detail=f"Book {item.book_id} not found")

        # Book Status Logic
        if transaction.transaction_type == TransactionType.ISSUE:
            if book.status != BookStatus.AVAILABLE:
                raise HTTPException(status_code=400, detail=f"Book '{book.title}' is not available")
            book.status = BookStatus.ISSUED

        elif transaction.transaction_type == TransactionType.RENEW:
            if book.status != BookStatus.ISSUED:
                raise HTTPException(status_code=400, detail=f"Book '{book.title}' cannot be renewed")
            book.status = BookStatus.ISSUED
            new_transaction.due_date = posting_date + timedelta(days=15)

        elif transaction.transaction_type == TransactionType.RETURN:
            book.status = BookStatus.AVAILABLE

        db.add(
            TransactionItem(
                transaction_id=new_transaction.id,
                book_id=book.id
            )
        )

        books_response.append(
            {
                "id": book.id,
                "title": book.title,
                "author": book.author,
                "isbn": book.isbn,
                "valuation_rate": book.valuation_rate,
                "status": book.status.value
            }
        )

    await db.commit()
    await db.refresh(new_transaction)

    return {
        "member": {
            "id": member.id,
            "full_name": member.full_name,
            "email": member.email,
            "membership_id": member.membership_id,
            "membership_type": member.membership_type.value,
            "total_unpaid_fines": member.total_unpaid_fines
        },
        "books": books_response,
        "posting_date": new_transaction.posting_date,
        "due_date": new_transaction.due_date,
        "transaction_type": new_transaction.transaction_type
    }

async def get_all_transactions(db: AsyncSession):
    # Eager load books
    result = await db.execute(
        select(Transaction)
        .options(
            selectinload(Transaction.member),  # load member with transaction
            selectinload(Transaction.books)) 
         # load books with transaction
    )
    transactions = result.scalars().all()

    transactions_list = []
    now = datetime.now(timezone.utc)

    for txn in transactions:
        member = await db.get(Member, txn.member_id)

        books_info = []
        issued_books_count = 0
        for book in txn.books:
            status_val = book.status.value if hasattr(book.status, "value") else str(book.status)
            if status_val.lower() == "issued":
                issued_books_count += 1
            books_info.append(
                {
                    "id": book.id,
                    "title": book.title,
                    "author": book.author,
                    "isbn": book.isbn,
                    "valuation_rate": book.valuation_rate,
                    "status": book.status
                }
            )

        # Calculate dynamic transaction fine
        transaction_fine = 0
        if issued_books_count > 0 and txn.due_date:
            txn_due_time = txn.due_date.replace(tzinfo=timezone.utc) if txn.due_date.tzinfo is None else txn.due_date
            if txn_due_time < now:
                days_overdue = (now.date() - txn_due_time.date()).days
                if days_overdue > 0:
                    transaction_fine = days_overdue * 2 * issued_books_count

        transactions_list.append(
            {
                "id": txn.id,
                "member_id": member.id if member else None,
                "member_name": member.full_name if member else None,
                "member_email": member.email if member else None,
                "posting_date": txn.posting_date,
                "due_date": txn.due_date,
                "transaction_type": txn.transaction_type.value if txn.transaction_type else None,
                "books": books_info,
                "total_fine": transaction_fine
            }
        )

    return transactions_list

async def get_transaction_by_id(db, transaction_id):

    result = await db.execute(
        select(Transaction)
        .where(Transaction.id == transaction_id)
        .options(
            selectinload(Transaction.member),
            selectinload(Transaction.books)
        )
    )

    return result.scalar_one_or_none()


async def update_transaction_mixed(db, transaction_id, books: List[TransactionUpdateRequestItem], due_date: datetime = None):
    txn = await db.get(Transaction, transaction_id, options=[selectinload(Transaction.books)])
    if not txn:
        raise Exception("Transaction not found")

    if due_date:
        if due_date.tzinfo is None:
            txn.due_date = due_date.replace(tzinfo=timezone.utc)
        else:
            txn.due_date = due_date

    for book_update in books:
        book_id = book_update.book_id
        action = book_update.transaction_type.upper()

        # Find the book in the transaction
        txn_book = next((b for b in txn.books if b.id == book_id), None)
        if not txn_book:
            continue

        # Update status
        if action == "RETURN":
            txn_book.status = BookStatus.AVAILABLE
        elif action == "ISSUE":
            txn_book.status = BookStatus.ISSUED
        elif action == "RENEW":
            txn_book.status = BookStatus.ISSUED
            txn.due_date = datetime.now(timezone.utc) + timedelta(days=15)

    await db.commit()


async def delete_transaction(db: AsyncSession, transaction_id: int):
    txn = await db.get(Transaction, transaction_id, options=[selectinload(Transaction.books)])
    if not txn:
        raise Exception("Transaction not found")

    # Reset books to AVAILABLE if transaction is being deleted
    for book in txn.books:
        book.status = BookStatus.AVAILABLE

    await db.delete(txn)
    await db.commit()
    return {"message": "Transaction deleted successfully"}
    