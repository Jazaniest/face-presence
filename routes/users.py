from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db
from models import User
from dependencies import get_current_user

router = APIRouter(prefix="/users", tags=["users"])

@router.get("/me")
def get_current_user_info(current_user: User = Depends(get_current_user)):
    """
    Endpoint untuk mendapatkan informasi user yang sedang login
    """
    return {
        "id": current_user.id,
        "user_name": current_user.user_name,
        "full_name": current_user.full_name,
        "role": current_user.role,
        "department_id": current_user.department_id,
        "manager_id": current_user.manager_id,
        "location_id": current_user.location_id
    }