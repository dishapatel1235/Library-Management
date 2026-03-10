from sqlalchemy import Column, Integer, ForeignKey, Enum, DateTime
from sqlalchemy.orm import relationship
from app.database import Base
from datetime import datetime
import enum

class TransactionType(str, enum.Enum):
    ISSUE = "ISSUE"
    RENEW = "RENEW"
    RETURN = "RETURN"

class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    member_id = Column(Integer, ForeignKey("members.id"))
    posting_date = Column(DateTime(timezone=True), default=datetime.utcnow)
    due_date = Column(DateTime(timezone=True), nullable=False)
    transaction_type = Column(Enum(TransactionType), nullable=False)

    books = relationship(
        "Book",
        secondary="transaction_items",
        back_populates="transactions"
    )

    member = relationship("Member", back_populates="transactions")



class TransactionItem(Base):
    __tablename__ = "transaction_items"

    transaction_id = Column(Integer, ForeignKey("transactions.id"), primary_key=True)
    book_id = Column(Integer, ForeignKey("books.id"), primary_key=True) # many to many relationship between transaction and book, as one transaction can have multiple books and one book can be part of multiple transactions 
