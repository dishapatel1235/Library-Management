import enum
from sqlalchemy import Column, Integer, String, Enum
from sqlalchemy.orm import relationship
from app.database import Base


class BookStatus(str, enum.Enum):
    AVAILABLE = "Available"
    ISSUED = "Issued"
    MAINTENANCE = "Maintenance"


class Book(Base):
    __tablename__ = "books"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    author = Column(String, nullable=False)
    isbn = Column(String, unique=True, nullable=False)
    status = Column(Enum(BookStatus), default=BookStatus.AVAILABLE)
    valuation_rate = Column(Integer, default=0)

    transactions = relationship(
        "Transaction",
        secondary="transaction_items",
        back_populates="books"
    )