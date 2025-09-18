from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional

from database import get_db
from models import User, Department, OfficeLocation
from dependencies import role_admin_required
from auth import get_password_hash
from fastapi import Form

router = APIRouter(prefix="/admin", tags=["admin"])


# ---------- Kepala Ruangan ----------
@router.get("/heads", response_model=List[dict])
def list_heads(db: Session = Depends(get_db), _=Depends(role_admin_required)):
    heads = db.query(User).filter(User.role == 'kepala_ruangan').all()
    return [{"id": h.id, "user_name": h.user_name, "full_name": h.full_name} for h in heads]



@router.post("/heads")
def create_head(
    user_name: str = Form(...),
    password: str = Form(...),
    full_name: str = Form(...),
    db: Session = Depends(get_db),
    _=Depends(role_admin_required)
):
    # cek username unik
    if db.query(User).filter(User.user_name == user_name).first():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username sudah digunakan.")
    hashed = get_password_hash(password)
    new = User(user_name=user_name, password=hashed, full_name=full_name, role='kepala_ruangan')
    db.add(new)
    db.commit()
    db.refresh(new)
    return {"message": "Kepala ruangan berhasil dibuat.", "id": new.id}



# ---------- Staff ----------
@router.get("/staff", response_model=List[dict])
def list_staff(db: Session = Depends(get_db), _=Depends(role_admin_required)):
    staffs = db.query(User).filter(User.role == 'staff').all()
    return [{"id": s.id, "user_name": s.user_name, "full_name": s.full_name, "manager_id": s.manager_id, "location_id": s.location_id} for s in staffs]


@router.post("/staff")
def create_staff(
    user_name: str = Form(...),
    password: str = Form(...),
    full_name: str = Form(...),
    manager_id: Optional[int] = Form(None),
    location_id: Optional[int] = Form(None),
    db: Session = Depends(get_db),
    _=Depends(role_admin_required)
):
    if db.query(User).filter(User.user_name == user_name).first():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username sudah digunakan.")
    
    hashed = get_password_hash(password)
    new = User(
        user_name=user_name,
        password=hashed,
        full_name=full_name,
        role='staff',
        manager_id=manager_id,
        location_id=location_id
    )
    db.add(new)
    db.commit()
    db.refresh(new)
    return {"message": "Staff berhasil dibuat.", "id": new.id}


@router.put("/staff/{staff_id}/assign-manager")
def assign_manager(staff_id: int, manager_id: int, db: Session = Depends(get_db), _=Depends(role_admin_required)):
    staff = db.query(User).filter(User.id == staff_id, User.role == 'staff').first()
    if not staff:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Staff tidak ditemukan.")
    manager = db.query(User).filter(User.id == manager_id, User.role == 'kepala_ruangan').first()
    if not manager:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Kepala ruangan tidak ditemukan.")
    staff.manager_id = manager_id
    db.commit()
    return {"message": "Assign manager berhasil."}


# ---------- Office Locations ----------
@router.get("/locations", response_model=List[dict])
def list_locations(db: Session = Depends(get_db), _=Depends(role_admin_required)):
    locs = db.query(OfficeLocation).all()
    return [{"id": l.id, "location_name": l.location_name, "latitude": l.latitude, "longitude": l.longitude, "radius_meters": l.radius_meters} for l in locs]


@router.post("/locations")
def create_location(location_name: str, latitude: float, longitude: float, radius_meters: int, db: Session = Depends(get_db), _=Depends(role_admin_required)):
    new = OfficeLocation(location_name=location_name, latitude=latitude, longitude=longitude, radius_meters=radius_meters)
    db.add(new)
    db.commit()
    db.refresh(new)
    return {"message": "Lokasi kantor berhasil dibuat.", "id": new.id}
