from fastapi import FastAPI
from fastapi.responses import FileResponse
from database import engine, Base

from routes import auth as auth_router
from routes import schedule as schedule_router
from routes import attendance as attendance_router
from routes import swap_requests as swap_requests_router
from routes import admin as admin_router
from routes import manager as manager_router
from routes import users as users_router

app = FastAPI(title="Sistem Absensi Wajah dengan MySQL (Modular)")

# membuat tabel saat pertama kali 
# Base.metadata.create_all(bind=engine)

# Include API routers
app.include_router(auth_router.router)
app.include_router(users_router.router)
app.include_router(schedule_router.router)
app.include_router(attendance_router.router)
app.include_router(swap_requests_router.router)
app.include_router(admin_router.router)
app.include_router(manager_router.router)

@app.get("/", include_in_schema=False)
async def serve_login():
    return FileResponse("login.html")

@app.get("/login", include_in_schema=False)
async def serve_login_alias():
    return FileResponse("login.html")

@app.get("/staff", include_in_schema=False)
async def serve_staff():
    return FileResponse("staff.html")

@app.get("/admin", include_in_schema=False)
async def serve_admin():
    return FileResponse("admin.html")

@app.get("/manager", include_in_schema=False)
async def serve_manager():
    return FileResponse("manager.html")
