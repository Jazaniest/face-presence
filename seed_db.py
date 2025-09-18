# seed_db.py
import json
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
# Pastikan main.py sudah diupdate ke versi MySQL
from database import DATABASE_URL
from models import User 

def seed_data():
    engine = create_engine(DATABASE_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()

    with open('face_embeddings.json', 'r') as f:
        data = json.load(f)

    for user_name, embedding in data.items():
        existing_user = db.query(User).filter(User.user_name == user_name).first()
        if existing_user:
            # Update embedding jika user_name cocok
            existing_user.embedding = embedding
            print(f"Update embedding untuk user: {user_name}")
        else:
            # Skip jika user_name tidak ada di DB
            print(f"User {user_name} tidak ditemukan di DB, dilewati.")

    
    db.commit()
    db.close()
    print("Proses seeding ke MySQL selesai.")

if __name__ == "__main__":
    seed_data()