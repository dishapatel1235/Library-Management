from pydantic import BaseModel
from datetime import datetime
from typing import List
from app.models import TransactionType

class TransactionBookItem(BaseModel):
    book_id: int

class TransactionCreate(BaseModel):
    member_id: int
    books: List[TransactionBookItem]
    due_date: datetime
    transaction_type: TransactionType

class TransactionBookResponse(BaseModel):
    id: int
    title: str
    author: str
    isbn: str
    valuation_rate: int
    status: str

class MemberInfo(BaseModel):
    id: int
    full_name: str
    email: str
    membership_id: str
    membership_type: str
    total_unpaid_fines: int

class BookInTransaction(BaseModel):
    id: int
    title: str
    author: str
    isbn: str
    valuation_rate: int
    status: str

class TransactionResponse(BaseModel):
    id: int
    member_id: int
    member_name: str
    member_email: str
    posting_date: datetime
    due_date: datetime
    transaction_type: str
    total_fine: int = 0
    books: List[BookInTransaction]

class BookTransactionUpdate(BaseModel):
    book_id: int
    transaction_type: str  # ISSUE / RENEW / RETURN

class TransactionUpdateRequest(BaseModel):
    member_id: int
    books: List[BookTransactionUpdate]
    transaction_type: TransactionType

class TransactionUpdateRequestItem(BaseModel):
    book_id: int
    transaction_type: str

    
# class TransactionResponse(BaseModel):
#     membership_id: int
#     full_name: str
#     email: str
#     title: str
#     author: str
#     isbn: str
#     valuation_rate: int
#     total_unpaid_fines: int
#     posting_date: datetime
#     due_date: datetime

    # class Config:
    #     orm_mode = True