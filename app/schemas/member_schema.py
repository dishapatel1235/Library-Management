from pydantic import BaseModel
from datetime import date
from app.models.members import MembershipType

class MemberCreate(BaseModel):
    full_name: str
    email: str
    membership_type: MembershipType
    
class MemberUpdate(BaseModel):
    full_name: str
    email: str
    membership_type: MembershipType

class MemberResponse(BaseModel):
    id: int
    full_name: str
    email: str
    membership_id: str
    membership_type: MembershipType
    starts_at: date
    expires_at: date
    total_unpaid_fines: int

    # class Config:
    #     orm_mode = True