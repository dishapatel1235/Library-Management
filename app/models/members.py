# Fields: Full Name, Email, Membership ID, Total Unpaid Fines
import enum
from datetime import datetime
from sqlalchemy import Column, Integer, String,Enum
from sqlalchemy.orm import relationship
from app.database import Base
from sqlalchemy import DateTime,Date, ForeignKey


class MembershipType(str, enum.Enum):
    Regular = "Regular" #2500/- per 5 years
    Premium = "Premium" #5000/- for lifetime


class Member(Base):
    __tablename__ = "members"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False)
    total_unpaid_fines = Column(Integer, default=0)
    transactions = relationship("Transaction", back_populates="member")

    membership_id = Column(String, unique=True, nullable=False)
    membership_type = Column(Enum(MembershipType), default=MembershipType.Regular)
    starts_at = Column(Date, default=datetime.utcnow)
    expires_at = Column(Date, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


