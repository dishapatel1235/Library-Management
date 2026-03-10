from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from app.models import Member
from datetime import datetime, timedelta, timezone
import uuid

from app.models.transaction import Transaction
from app.schemas import MemberResponse

#if due_date - posting_date> 15 days then total_unpaid_fines=((due_date - posting_date-15)*10)/100 rupee (added paisa to rupee converter logic)
async def create_member(db, members):
    membership_id = "MEM-" + str(uuid.uuid4())[:8]
    
    if members.membership_type == "Regular":
        expires_at = datetime.utcnow().date() + timedelta(days=1825)  # 5 years
    else:
        expires_at = datetime.utcnow().date() + timedelta(days=36500) # lifetime

    total_unpaid_fines=0
    new_member = Member(
        full_name=members.full_name,
        email=members.email,
        membership_id=membership_id,
        membership_type=members.membership_type,
        total_unpaid_fines=total_unpaid_fines,
        expires_at=expires_at
        
    )

    db.add(new_member)
    await db.commit()
    await db.refresh(new_member)

    return new_member


async def get_members(db):
    result = await db.execute(select(Member))
    members = result.scalars().all()

    # Load all transactions to calculate dynamic fines
    tx_result = await db.execute(select(Transaction).options(selectinload(Transaction.books)))
    transactions = tx_result.scalars().all()
    now = datetime.utcnow().replace(tzinfo=timezone.utc)

    # Calculate fines per member
    member_fines = {m.id: 0 for m in members}
    
    for txn in transactions:
        if txn.member_id in member_fines and txn.due_date:
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
                        member_fines[txn.member_id] += (days_overdue * 2 * issued_books_count)
    
    changed = False
    for member in members:
        calc_fine = member_fines.get(member.id, 0)
        if member.total_unpaid_fines != calc_fine:
            member.total_unpaid_fines = calc_fine
            changed = True
            
    if changed:
        await db.commit()
        for member in members:
            await db.refresh(member)
        
    return members


async def update_member(db, member_id, member_data):
    result = await db.execute(select(Member).where(Member.id == member_id))
    member = result.scalar_one_or_none()

    if not member:
        return None

    member.full_name = member_data.full_name
    member.email = member_data.email
    member.membership_type = member_data.membership_type

    # update expiry if membership type changes
    if member_data.membership_type == "Regular":
        member.expires_at = datetime.utcnow().date() + timedelta(days=1825)
    else:
        member.expires_at = datetime.utcnow().date() + timedelta(days=36500)

    await db.commit()
    await db.refresh(member)

    return member


async def delete_member(db, member_id):
    result = await db.execute(select(Member).where(Member.id == member_id))
    member = result.scalar_one_or_none()

    if not member:
        return None

    await db.delete(member)
    await db.commit()

    return {"message": "Member deleted successfully"}