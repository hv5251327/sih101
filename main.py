import os
import json
from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional
from sqlalchemy import create_engine, Column, Integer, String, Text, func
from sqlalchemy.orm import declarative_base, sessionmaker, Session

app = FastAPI(title="MoSPI iGOT Intelligence Platform")

# Comprehensive CORS setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./igot_mospi.db")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+psycopg2://", 1)
elif DATABASE_URL.startswith("postgresql://") and not DATABASE_URL.startswith("postgresql+psycopg2://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg2://", 1)

connect_args = {"check_same_thread": False} if "sqlite" in DATABASE_URL else {"sslmode": "require"}
engine = create_engine(DATABASE_URL, connect_args=connect_args, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class UserRecord(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(255), nullable=True)
    email = Column(String(255), unique=True, index=True, nullable=True)
    password = Column(String(255), nullable=True)
    hashed_password = Column(String(255), nullable=True)
    department = Column(String(255), default="National Accounts Division (NAD)")
    designation = Column(String(255), default="Deputy Director / Assistant Director (ISS)")
    cadre = Column(String(100), default="Indian Statistical Service (ISS)")
    role = Column(String(50), default="employee")
    competency_score = Column(String(10), default="75%")
    posh_status = Column(String(50), default="Pending")
    completed_modules = Column(Text, default="[]")

class QuizRecord(Base):
    __tablename__ = "topic_quizzes"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    course_id = Column(Integer, nullable=False, default=1)
    question = Column(Text, nullable=False)
    options_json = Column(Text, nullable=False)
    correct_index = Column(Integer, default=0)
    explanation = Column(Text, default="")

try:
    Base.metadata.create_all(bind=engine)
except Exception as e:
    print(f"Table sync warning: {e}")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class RegisterRequest(BaseModel):
    name: Optional[str] = "Registered Officer"
    email: str
    password: str
    department: Optional[str] = "National Accounts Division (NAD)"
    designation: Optional[str] = "Deputy Director / Assistant Director (ISS)"
    cadre: Optional[str] = "Indian Statistical Service (ISS)"

class LoginRequest(BaseModel):
    email: str
    password: str

@app.get("/")
def root():
    return {"status": "online", "platform": "iGOT MoSPI Intelligence"}

@app.post("/api/register")
def register(req: RegisterRequest, db: Session = Depends(get_db)):
    clean_email = req.email.strip().lower()
    clean_pass = req.password.strip()

    if not clean_email or not clean_pass:
        raise HTTPException(status_code=400, detail="Email and password cannot be empty.")

    existing = db.query(UserRecord).filter(func.lower(UserRecord.email) == clean_email).first()
    if existing:
        raise HTTPException(status_code=400, detail="An account with this email already exists.")

    role = "admin" if clean_email == "123@gov.ac.in" else "employee"

    user = UserRecord(
        name=req.name.strip() if req.name else "Registered Officer",
        email=clean_email,
        password=clean_pass,
        hashed_password=clean_pass,
        department=req.department.strip() if req.department else "National Accounts Division (NAD)",
        designation=req.designation.strip() if req.designation else "Deputy Director / Assistant Director (ISS)",
        cadre=req.cadre.strip() if req.cadre else "Indian Statistical Service (ISS)",
        role=role,
        competency_score="75%",
        posh_status="Pending",
        completed_modules="[]"
    )

    try:
        db.add(user)
        db.commit()
        db.refresh(user)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

    return {
        "status": "success",
        "user": {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "department": user.department,
            "designation": user.designation,
            "cadre": user.cadre,
            "role": user.role,
            "competency_score": user.competency_score,
            "posh_status": user.posh_status,
            "completed_modules": []
        }
    }

@app.post("/api/login")
def login(req: LoginRequest, db: Session = Depends(get_db)):
    clean_email = req.email.strip().lower()
    clean_pass = req.password.strip()

    if clean_email == "123@gov.ac.in" and clean_pass == "1234":
        return {
            "status": "success",
            "user": {
                "id": 999,
                "name": "Chief Administrator",
                "email": "123@gov.ac.in",
                "department": "Ministry Headquarters",
                "designation": "Director General",
                "cadre": "Indian Statistical Service (ISS)",
                "role": "admin",
                "competency_score": "100%",
                "posh_status": "Completed",
                "completed_modules": [1, 2, 3]
            }
        }

    user = db.query(UserRecord).filter(func.lower(UserRecord.email) == clean_email).first()
    if not user:
        raise HTTPException(status_code=401, detail="No user found with this email.")

    stored_pass = (user.password or user.hashed_password or "").strip()
    if stored_pass != clean_pass:
        raise HTTPException(status_code=401, detail="Invalid password.")

    try:
        completed = json.loads(user.completed_modules) if user.completed_modules else []
    except Exception:
        completed = []

    return {
        "status": "success",
        "user": {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "department": user.department,
            "designation": user.designation,
            "cadre": user.cadre,
            "role": user.role,
            "competency_score": user.competency_score,
            "posh_status": user.posh_status,
            "completed_modules": completed
        }
    }

@app.get("/api/admin/users")
def get_all_users(db: Session = Depends(get_db)):
    users = db.query(UserRecord).all()
    course_titles = {
        1: "System of National Accounts & GDP (NAD)",
        2: "Consumer Price Index (CPI) Analytics",
        3: "PLFS Digital Data Collection (FOD)",
        4: "Annual Survey of Industries (ASI)",
        5: "Index of Industrial Production (IIP)"
    }
    results = []
    for u in users:
        try:
            completed_ids = json.loads(u.completed_modules) if u.completed_modules else []
        except Exception:
            completed_ids = []

        learned_topics = [course_titles.get(cid, f"Module #{cid}") for cid in completed_ids]

        results.append({
            "id": u.id,
            "name": u.name or "Officer",
            "email": u.email,
            "cadre": u.cadre or "ISS",
            "designation": u.designation or "Director",
            "department": u.department or "MoSPI",
            "competency": u.competency_score or "75%",
            "posh": u.posh_status or "Pending",
            "role": u.role or "employee",
            "completed_count": len(completed_ids),
            "learned_topics": learned_topics
        })
    return results
