from fastapi import APIRouter, Depends, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas import MemberCreate, MemberResponse, MemberUpdate
from app.services import member_service

router = APIRouter()

templates = Jinja2Templates(directory="app/templates")


# LIST MEMBERS PAGE
@router.get("/members", response_class=HTMLResponse)
async def members_page(request: Request, db: AsyncSession = Depends(get_db)):

    members = await member_service.get_members(db)

    return templates.TemplateResponse(
        "members.html",
        {"request": request, "members": members}
    )


# ADD MEMBER FORM PAGE
@router.get("/members/add", response_class=HTMLResponse)
async def add_member_page(request: Request):

    return templates.TemplateResponse(
        "member_form.html",
        {"request": request, "member": None}
    )


# CREATE MEMBER (FORM SUBMIT)
@router.post("/members/add")
async def create_member_ui(
    request: Request,
    full_name: str = Form(...),
    email: str = Form(...),
    membership_type: str = Form(...),
    db: AsyncSession = Depends(get_db)
):
    try:
        member = MemberCreate(
            full_name=full_name,
            email=email,
            membership_type=membership_type
        )

        await member_service.create_member(db, member)
        return RedirectResponse("/members", status_code=303)
        
    except Exception as e:
        return templates.TemplateResponse(
            "member_form.html",
            {
                "request": request,
                "member": None,
                "error": str(e.detail) if hasattr(e, 'detail') else str(e)
            }
        )


# EDIT MEMBER PAGE
@router.get("/members/edit/{member_id}", response_class=HTMLResponse)
async def edit_member_page(request: Request, member_id: int, db: AsyncSession = Depends(get_db)):

    members = await member_service.get_members(db)
    member = next((m for m in members if m.id == member_id), None)

    if not member:
        raise HTTPException(status_code=404, detail="Member not found")

    return templates.TemplateResponse(
        "member_form.html",
        {"request": request, "member": member}
    )


# UPDATE MEMBER (FORM SUBMIT)
@router.post("/members/update/{member_id}")
async def update_member_ui(
    request: Request,
    member_id: int,
    full_name: str = Form(...),
    email: str = Form(...),
    membership_type: str = Form(...),
    db: AsyncSession = Depends(get_db)
):
    try:
        member_update = MemberUpdate(
            full_name=full_name,
            email=email,
            membership_type=membership_type
        )

        await member_service.update_member(db, member_id, member_update)
        return RedirectResponse("/members", status_code=303)
        
    except Exception as e:
        members = await member_service.get_members(db)
        member = next((m for m in members if m.id == member_id), None)
        return templates.TemplateResponse(
            "member_form.html",
            {
                "request": request,
                "member": member,
                "error": str(e.detail) if hasattr(e, 'detail') else str(e)
            }
        )


# DELETE MEMBER
@router.get("/members/delete/{member_id}")
async def delete_member_ui(member_id: int, db: AsyncSession = Depends(get_db)):

    await member_service.delete_member(db, member_id)

    return RedirectResponse("/members", status_code=303)


@router.post("/create_members", response_model=MemberResponse)
async def create_member(member: MemberCreate, db: AsyncSession = Depends(get_db)):
    return await member_service.create_member(db, member)


@router.get("/list_members", response_model=List[MemberResponse])
async def list_members(db: AsyncSession = Depends(get_db)):
    return await member_service.get_members(db)


@router.put("/update_member/{member_id}", response_model=MemberResponse)
async def update_member(member_id: int, member: MemberUpdate, db: AsyncSession = Depends(get_db)):
    updated_member = await member_service.update_member(db, member_id, member)

    if not updated_member:
        raise HTTPException(status_code=404, detail="Member not found")

    return updated_member


@router.delete("/delete_member/{member_id}")
async def delete_member(member_id: int, db: AsyncSession = Depends(get_db)):
    deleted_member = await member_service.delete_member(db, member_id)

    if not deleted_member:
        raise HTTPException(status_code=404, detail="Member not found")

    return deleted_member

# router = APIRouter()

# @router.post("/create_members",response_model=MemberResponse)
# async def create_member(member: MemberCreate, db: AsyncSession = Depends(get_db)):
#     return await member_service.create_member(db, member)

# @router.get("/list_members",response_model=List[MemberResponse])
# async def list_members(db: AsyncSession = Depends(get_db)):
#     return await member_service.get_member(db)

# @router.put("/update_member/{member_id}", response_model=MemberResponse)
# async def update_member(member_id: int, member: MemberUpdate, db: AsyncSession = Depends(get_db)):
#     updated_member = await member_service.update_member(db, member_id, member)

#     if not updated_member:
#         raise HTTPException(status_code=404, detail="Member not found")

#     return updated_member


# @router.delete("/delete_member/{member_id}")
# async def delete_member(member_id: int, db: AsyncSession = Depends(get_db)):
#     deleted_member = await member_service.delete_member(db, member_id)

#     if not deleted_member:
#         raise HTTPException(status_code=404, detail="Member not found")

#     return deleted_member