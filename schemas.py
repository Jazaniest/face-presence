from pydantic import BaseModel
from datetime import date, time, datetime

class ScheduleBase(BaseModel):
    user_id: int
    shift_date: date
    start_time: time
    end_time: time

class ScheduleCreate(ScheduleBase):
    pass

class ScheduleResponse(ScheduleBase):
    id: int

    class Config:
        from_attributes = True

class SwapRequestCreate(BaseModel):
    requested_id: int
    requester_schedule_id: int
    requested_schedule_id: int

class SwapRequestResponse(BaseModel):
    id: int
    requester_id: int
    requested_id: int
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str
