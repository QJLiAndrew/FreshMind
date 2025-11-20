from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional
from uuid import UUID
from pydantic import BaseModel

from backend.app.database import get_db
from backend.app.models import User

router = APIRouter(prefix="/api/users", tags=["users"])


# --- Pydantic Schemas for this router ---
class UserProfileUpdate(BaseModel):
    unit_preference: Optional[str] = None
    is_vegan: Optional[bool] = None
    is_vegetarian: Optional[bool] = None
    is_gluten_free: Optional[bool] = None
    is_dairy_free: Optional[bool] = None
    is_halal: Optional[bool] = None
    is_kosher: Optional[bool] = None
    daily_calorie_goal: Optional[int] = None
    daily_protein_goal: Optional[int] = None


class UserProfileResponse(BaseModel):
    user_id: UUID
    username: str
    email: str
    is_vegan: bool
    is_vegetarian: bool
    is_gluten_free: bool
    is_halal: bool
    daily_calorie_goal: int

    class Config:
        from_attributes = True


# ==========================================
# ENDPOINTS
# ==========================================

@router.get("/{user_id}", response_model=UserProfileResponse)
async def get_user_profile(
        user_id: str,
        db: Session = Depends(get_db)
):
    """Get user profile and preferences"""
    user = db.query(User).filter(User.user_id == UUID(user_id)).first()
    if not user:
        raise HTTPException(404, "User not found")
    return user


@router.patch("/{user_id}", response_model=UserProfileResponse)
async def update_user_profile(
        user_id: str,
        updates: UserProfileUpdate,
        db: Session = Depends(get_db)
):
    """Update user dietary preferences and goals"""
    user = db.query(User).filter(User.user_id == UUID(user_id)).first()
    if not user:
        raise HTTPException(404, "User not found")

    # Apply updates dynamically
    update_data = updates.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(user, key, value)

    db.commit()
    db.refresh(user)
    return user