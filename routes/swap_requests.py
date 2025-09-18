import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database import get_db
from models import ShiftSwapRequest, Schedule, User
from schemas import SwapRequestCreate, SwapRequestResponse
from dependencies import get_current_user, role_manager_or_admin_required

router = APIRouter(prefix="/swap-requests", tags=["swap_requests"])


@router.post("/", response_model=SwapRequestResponse)
def create_swap_request(
    request_data: SwapRequestCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.id == request_data.requested_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Anda tidak bisa tukar jadwal dengan diri sendiri.")

    requester_schedule = db.query(Schedule).filter(
        Schedule.id == request_data.requester_schedule_id,
        Schedule.user_id == current_user.id
    ).first()
    if not requester_schedule:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Jadwal yang Anda ajukan tidak ditemukan.")

    new_request = ShiftSwapRequest(
        requester_id=current_user.id,
        requested_id=request_data.requested_id,
        requester_schedule_id=request_data.requester_schedule_id,
        requested_schedule_id=request_data.requested_schedule_id,
        status='pending_manager'
    )
    db.add(new_request)
    db.commit()
    db.refresh(new_request)
    return new_request


@router.put("/{request_id}/approve")
def approve_swap_request(
    request_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(role_manager_or_admin_required)
):
    swap_request = db.query(ShiftSwapRequest).filter(ShiftSwapRequest.id == request_id).first()
    if not swap_request:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Permintaan tidak ditemukan.")

    requester_schedule = db.query(Schedule).filter(Schedule.id == swap_request.requester_schedule_id).first()
    requested_schedule = db.query(Schedule).filter(Schedule.id == swap_request.requested_schedule_id).first()

    if not requester_schedule or not requested_schedule:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Salah satu jadwal yang akan ditukar tidak ditemukan.")

    original_requester_id = requester_schedule.user_id
    requester_schedule.user_id = requested_schedule.user_id
    requested_schedule.user_id = original_requester_id

    swap_request.status = 'approved'

    db.commit()
    return {"message": "Tukar jadwal berhasil disetujui dan jadwal telah diperbarui."}


@router.put("/{request_id}/reject")
def reject_swap_request(
    request_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(role_manager_or_admin_required)
):
    """
    Reject a swap request (manager or admin).
    """
    swap_request = db.query(ShiftSwapRequest).filter(ShiftSwapRequest.id == request_id).first()
    if not swap_request:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Permintaan tidak ditemukan.")

    swap_request.status = 'rejected'
    db.commit()
    return {"message": "Permintaan tukar jadwal ditolak."}


@router.get("/pending/manager")
def get_pending_for_manager(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List semua permintaan tukar yang statusnya 'pending_manager' dan
    melibatkan staff yang dikelola oleh current_user (sebagai manager).
    Manager akan melihat permintaan di mana requester_id atau requested_id
    adalah subordinate mereka.
    """
    subordinates = db.query(User.id).filter(User.manager_id == current_user.id).all()
    subordinate_ids = [s.id for s in subordinates]

    if not subordinate_ids:
        return []

    pending = db.query(ShiftSwapRequest).filter(
        ShiftSwapRequest.status == 'pending_manager',
        ((ShiftSwapRequest.requester_id.in_(subordinate_ids)) | (ShiftSwapRequest.requested_id.in_(subordinate_ids)))
    ).all()

    result = []
    for r in pending:
        result.append({
            "id": r.id,
            "requester_id": r.requester_id,
            "requested_id": r.requested_id,
            "requester_schedule_id": r.requester_schedule_id,
            "requested_schedule_id": r.requested_schedule_id,
            "status": r.status,
            "created_at": r.created_at
        })
    return result
