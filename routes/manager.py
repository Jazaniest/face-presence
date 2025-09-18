from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
import datetime

from database import get_db
from dependencies import get_current_user, role_manager_or_admin_required
from models import User, Attendance, Schedule
from fastapi import Response, Form

router = APIRouter(prefix="/manager", tags=["manager"])


@router.get("/subordinates", response_model=List[dict])
def list_subordinates(
    db: Session = Depends(get_db),
    current_user: User = Depends(role_manager_or_admin_required)
):
    """
    List semua staff yang berada di bawah kepala_ruangan saat ini.
    """
    subs = db.query(User).filter(User.manager_id == current_user.id).all()
    result = []
    for s in subs:
        result.append({
            "id": s.id,
            "user_name": s.user_name,
            "full_name": s.full_name,
            "role": s.role,
            "department_id": s.department_id
        })
    return result


@router.get("/subordinates/{user_id}/attendances")
def get_subordinate_attendances(
    user_id: int,
    year: Optional[int] = Query(None),
    month: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(role_manager_or_admin_required)
):
    """
    Mendapatkan daftar absensi untuk subordinate tertentu dalam rentang bulan/tahun tertentu.
    Jika year/month tidak diberikan, return 30 hari terakhir.
    """

    subordinate = db.query(User).filter(User.id == user_id, User.manager_id == current_user.id).first()
    if not subordinate:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User bukan bawahan Anda atau tidak ditemukan.")

    query = db.query(Attendance).filter(Attendance.user_id == user_id)

    if year and month:
        try:
            start_date = datetime.date(year, month, 1)
            if month == 12:
                end_date = datetime.date(year + 1, 1, 1) - datetime.timedelta(days=1)
            else:
                end_date = datetime.date(year, month + 1, 1) - datetime.timedelta(days=1)
            query = query.filter(db.func.date(Attendance.timestamp) >= start_date, db.func.date(Attendance.timestamp) <= end_date)
        except ValueError:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Tahun atau bulan tidak valid.")
    else:
        cutoff = datetime.datetime.utcnow() - datetime.timedelta(days=30)
        query = query.filter(Attendance.timestamp >= cutoff)

    records = query.order_by(Attendance.timestamp.desc()).all()
    res = []
    for r in records:
        res.append({
            "id": r.id,
            "timestamp": r.timestamp,
            "latitude": r.latitude,
            "longitude": r.longitude
        })
    return res


@router.post("/schedules")
def create_schedule_for_subordinate(
    user_id: int = Form(...),
    shift_date: str = Form(...),
    start_time: str = Form(...),
    end_time: str = Form(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(role_manager_or_admin_required)
):
    """
    Kepala Ruangan membuat jadwal untuk staff. Format tanggal/time string ISO (YYYY-MM-DD, HH:MM:SS or HH:MM).
    Note: Kita bisa memanggil endpoint /schedules/ yang sudah ada, tapi endpoint terpisah ini memberikan UX yang jelas.
    """
    subordinate = db.query(User).filter(User.id == user_id, User.manager_id == current_user.id).first()
    if not subordinate:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User bukan staff Anda atau tidak ditemukan.")

    try:
        shift_date_dt = datetime.datetime.strptime(shift_date, "%Y-%m-%d").date()
        start_time_dt = datetime.datetime.strptime(start_time, "%H:%M").time()
        end_time_dt = datetime.datetime.strptime(end_time, "%H:%M").time()
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Format tanggal atau waktu tidak valid. Gunakan YYYY-MM-DD dan HH:MM.")

    new_schedule = Schedule(user_id=user_id, shift_date=shift_date_dt, start_time=start_time_dt, end_time=end_time_dt)
    db.add(new_schedule)
    db.commit()
    db.refresh(new_schedule)

    return {"message": "Jadwal berhasil dibuat untuk staff.", "schedule_id": new_schedule.id}
