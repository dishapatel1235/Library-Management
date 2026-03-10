from pydantic import BaseModel
from enum import Enum


class BookStatus(str, Enum):
    AVAILABLE = "Available"
    ISSUED = "Issued"
    MAINTENANCE = "Maintenance"


class BookCreate(BaseModel):
    title: str
    author: str
    isbn: str
    valuation_rate: int

class BookUpdate(BaseModel):
    title: str
    author: str
    isbn: str
    valuation_rate: int
    # status: BookStatus
    
class BookResponse(BookCreate):
    id: int
    title: str
    author: str
    isbn: str
    valuation_rate: int
    status: BookStatus
