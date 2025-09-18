import datetime
import io
from typing import Any

import numpy as np
import cv2
import face_recognition
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Form, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from fastapi.responses import StreamingResponse

from database import get_db
from models import Attendance, Schedule, User
from dependencies import get_current_user
from utils import haversine_distance

router = APIRouter(prefix="/attendance", tags=["attendance"])


@router.post("/check-requirements")
async def check_attendance_requirements(
    attendance_type: str = Form(...),
    latitude: float = Form(...),
    longitude: float = Form(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    Endpoint untuk verifikasi persyaratan absensi sebelum verifikasi wajah:
    - Role check
    - Schedule check
    - Time check
    - Location check
    - Previous attendance check
    """
    if current_user.role != "staff":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Hanya staff yang bisa melakukan absensi.")

    today = datetime.date.today()
    schedule = db.query(Schedule).filter(
        Schedule.user_id == current_user.id,
        Schedule.shift_date == today
    ).first()

    if not schedule:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Anda tidak memiliki jadwal kerja hari ini ({today}).")

    now_time = datetime.datetime.now().time()
    
    if attendance_type == "masuk":
        # Toleransi sebelum start untuk absen masuk
        allowed_start_time = (datetime.datetime.combine(today, schedule.start_time) - datetime.timedelta(minutes=30)).time()
        # Bisa absen masuk sampai
        allowed_end_time = (datetime.datetime.combine(today, schedule.start_time) + datetime.timedelta(minutes=30)).time()
        
        if not (allowed_start_time <= now_time <= allowed_end_time):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Absen masuk hanya bisa dilakukan antara jam {allowed_start_time} - {allowed_end_time}."
            )
    
    elif attendance_type == "pulang":
        # Absen pulang bisa dilakukan
        allowed_start_time = (datetime.datetime.combine(today, schedule.end_time) - datetime.timedelta(hours=1)).time()
        # Sampai setelah jadwal berakhir
        allowed_end_time = (datetime.datetime.combine(today, schedule.end_time) + datetime.timedelta(hours=1)).time()
        
        if not (allowed_start_time <= now_time <= allowed_end_time):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Absen pulang hanya bisa dilakukan antara jam {allowed_start_time} - {allowed_end_time}."
            )
    else:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Jenis absensi tidak valid. Gunakan 'masuk' atau 'pulang'.")

    office_location = current_user.office_location
    if not office_location:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Lokasi kantor Anda belum diatur. Hubungi admin.")

    distance = haversine_distance(latitude, longitude, office_location.latitude, office_location.longitude)
    if distance > office_location.radius_meters:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Anda berada di luar jangkauan lokasi kantor ({int(distance)} meter)."
        )

    today_attendance = db.query(Attendance).filter(
        Attendance.user_id == current_user.id,
        func.date(Attendance.timestamp) == today
    ).order_by(Attendance.timestamp.desc()).all()

    if attendance_type == "masuk":
        masuk_attendance = [a for a in today_attendance if a.attendance_type == "masuk"]
        if masuk_attendance:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Anda sudah melakukan absen masuk hari ini.")
    
    elif attendance_type == "pulang":
        masuk_attendance = [a for a in today_attendance if a.attendance_type == "masuk"]
        pulang_attendance = [a for a in today_attendance if a.attendance_type == "pulang"]
        
        if not masuk_attendance:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Anda harus absen masuk terlebih dahulu.")
        
        if pulang_attendance:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Anda sudah melakukan absen pulang hari ini.")

    if not current_user.embedding:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Wajah Anda belum terdaftar. Hubungi admin.")

    return {
        "status": "requirements_met",
        "message": "Semua persyaratan terpenuhi. Silakan lanjut ke verifikasi wajah.",
        "attendance_type": attendance_type,
        "schedule": {
            "start_time": str(schedule.start_time),
            "end_time": str(schedule.end_time)
        }
    }


@router.post("/submit")
async def submit_attendance(
    file: UploadFile = File(...),
    attendance_type: str = Form(...),
    latitude: float = Form(...),
    longitude: float = Form(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    Endpoint untuk submit absensi setelah verifikasi wajah
    """
    try:
        await check_attendance_requirements(attendance_type, latitude, longitude, db, current_user)
    except HTTPException as e:
        raise e

    contents = await file.read()
    image_array = np.frombuffer(contents, np.uint8)
    image = cv2.imdecode(image_array, cv2.IMREAD_COLOR)
    if image is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File gambar tidak valid atau tidak dapat dibaca.")

    rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

    face_locations = face_recognition.face_locations(rgb_image)
    if not face_locations:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Wajah tidak terdeteksi di gambar.")

    unknown_embedding = face_recognition.face_encodings(rgb_image, face_locations)[0]
    known_embedding = np.array(current_user.embedding)

    is_match = face_recognition.compare_faces([known_embedding], unknown_embedding, tolerance=0.5)[0]
    if not is_match:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Verifikasi wajah gagal.")

    # Simpan absensi
    new_attendance = Attendance(
        user_id=current_user.id,
        attendance_type=attendance_type,
        latitude=latitude,
        longitude=longitude
    )
    db.add(new_attendance)
    db.commit()
    db.refresh(new_attendance)

    return {
        "status": "success",
        "user_name": current_user.full_name,
        "attendance_type": attendance_type,
        "timestamp": new_attendance.timestamp
    }


@router.post("/check")
async def check_attendance_legacy(
    file: UploadFile = File(...),
    latitude: float = Form(...),
    longitude: float = Form(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    Legacy endpoint - redirect ke submit dengan attendance_type masuk
    """
    return await submit_attendance(file, "masuk", latitude, longitude, db, current_user)