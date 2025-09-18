import datetime
from sqlalchemy import (
    Column, Integer, String, DateTime, ForeignKey, JSON, Enum, Date, Time, Float
)
from sqlalchemy.orm import relationship
from database import Base

class Department(Base):
    __tablename__ = "departments"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), unique=True, nullable=False)

    users = relationship("User", back_populates="department")


class OfficeLocation(Base):
    __tablename__ = "office_locations"
    id = Column(Integer, primary_key=True, index=True)
    location_name = Column(String(255), nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    radius_meters = Column(Integer, nullable=False)

    users = relationship("User", back_populates="office_location")


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    user_name = Column(String(255), unique=True, index=True, nullable=False)
    password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=False)
    embedding = Column(JSON, nullable=True) 
    role = Column(Enum('admin', 'kepala_ruangan', 'staff', name='user_roles'), nullable=False)

    # Foreign Keys
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=True)
    manager_id = Column(Integer, ForeignKey("users.id"), nullable=True) 
    location_id = Column(Integer, ForeignKey("office_locations.id"), nullable=True)

    # Relasi SQLAlchemy
    department = relationship("Department", back_populates="users")
    office_location = relationship("OfficeLocation", back_populates="users")
    schedules = relationship("Schedule", back_populates="user")
    attendances = relationship("Attendance", back_populates="user")

    # Relasi self-referential (manager)
    manager = relationship("User", remote_side=[id], backref="subordinates", uselist=False)


class Schedule(Base):
    __tablename__ = "schedules"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    shift_date = Column(Date, nullable=False)
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)

    # Relasi SQLAlchemy
    user = relationship("User", back_populates="schedules")


class Attendance(Base):
    __tablename__ = "attendance"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    attendance_type = Column(Enum('masuk', 'pulang', name='attendance_types'), nullable=False, default='masuk')
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    latitude = Column(Float)
    longitude = Column(Float)

    # Relasi SQLAlchemy
    user = relationship("User", back_populates="attendances")


class ShiftSwapRequest(Base):
    __tablename__ = "shift_swap_requests"
    id = Column(Integer, primary_key=True, index=True)
    requester_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    requested_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    requester_schedule_id = Column(Integer, ForeignKey("schedules.id"), nullable=False)
    requested_schedule_id = Column(Integer, ForeignKey("schedules.id"), nullable=False)
    status = Column(
        Enum('pending_manager', 'approved', 'rejected', name='swap_statuses'),
        default='pending_manager'
    )
    created_at = Column(DateTime, default=datetime.datetime.utcnow)