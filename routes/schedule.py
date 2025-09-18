from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
import datetime

from database import get_db
from models import Schedule, User
from schemas import ScheduleCreate, ScheduleResponse
from dependencies import role_manager_or_admin_required, get_current_user

router = APIRouter(prefix="/schedules", tags=["schedules"])


@router.post("/", response_model=ScheduleResponse)
def create_schedule(
    schedule: ScheduleCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(role_manager_or_admin_required)
):
    """
    Membuat jadwal baru untuk seorang staff.
    Hanya Admin atau Kepala Ruangan yang bisa mengakses.
    """
    if current_user.role == "kepala_ruangan":
        staff_to_schedule = db.query(User).filter(User.id == schedule.user_id).first()
        if not staff_to_schedule or staff_to_schedule.manager_id != current_user.id:
            raise HTTPException(status_code=403, detail="Anda hanya bisa membuat jadwal untuk staff Anda.")

    new_schedule = Schedule(**schedule.dict())
    db.add(new_schedule)
    db.commit()
    db.refresh(new_schedule)
    return new_schedule


@router.get("/user/{user_id}", response_model=List[ScheduleResponse])
def get_schedules_for_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Melihat jadwal untuk user tertentu.
    - Staff hanya bisa melihat jadwal mereka sendiri
    - Manager/Admin bisa melihat jadwal staff mereka
    """
    if current_user.role == "staff" and current_user.id != user_id:
        raise HTTPException(status_code=403, detail="Anda hanya bisa melihat jadwal Anda sendiri.")
    
    if current_user.role == "kepala_ruangan":
        if current_user.id != user_id: 
            staff_to_view = db.query(User).filter(User.id == user_id).first()
            if not staff_to_view or staff_to_view.manager_id != current_user.id:
                raise HTTPException(status_code=403, detail="Anda hanya bisa melihat jadwal staff Anda.")

    schedules = db.query(Schedule).filter(Schedule.user_id == user_id).all()
    return schedules


# Endpoint untuk backward compatibility (untuk manager/admin)
@router.get("/{user_id}", response_model=List[ScheduleResponse])
def get_schedules_admin(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(role_manager_or_admin_required)
):
    """
    Endpoint khusus untuk manager/admin melihat jadwal staff.
    """
    if current_user.role == "kepala_ruangan":
        staff_to_view = db.query(User).filter(User.id == user_id).first()
        if not staff_to_view or staff_to_view.manager_id != current_user.id:
            raise HTTPException(status_code=403, detail="Anda hanya bisa melihat jadwal staff Anda.")

    schedules = db.query(Schedule).filter(Schedule.user_id == user_id).all()
    return schedules