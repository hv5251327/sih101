import os
import io
import json
import re
from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from openai import OpenAI
from pypdf import PdfReader
from sqlalchemy import create_engine, Column, Integer, String, Text
from sqlalchemy.orm import declarative_base, sessionmaker, Session

app = FastAPI(title="MoSPI AI Skill Intelligence & iGOT Platform")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./igot_mospi.db")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(
    DATABASE_URL, 
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class UserRecord(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password = Column(String(255), nullable=False)
    department = Column(String(255), default="National Accounts Division (NAD)")
    designation = Column(String(255), default="Deputy Director / Assistant Director (ISS)")
    cadre = Column(String(100), default="Indian Statistical Service (ISS)")
    role = Column(String(50), default="employee")
    competency_score = Column(String(10), default="75%")
    posh_status = Column(String(50), default="Pending")

class TopicQuizRecord(Base):
    __tablename__ = "topic_quizzes"
    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(Integer, index=True)
    question = Column(Text, nullable=False)
    options_json = Column(Text, nullable=False)
    correct_index = Column(Integer, default=0)
    explanation = Column(Text, nullable=False)

Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.on_event("startup")
def startup_seeding():
    db = SessionLocal()
    try:
        if not db.query(UserRecord).filter(UserRecord.email == "123@gov.ac.in").first():
            db.add(UserRecord(
                name="Master Administrator",
                email="123@gov.ac.in",
                password="1234",
                department="Capacity Building Commission",
                designation="Chief Administrator",
                cadre="Commission",
                role="admin",
                competency_score="100%",
                posh_status="Completed"
            ))
        db.commit()
    except Exception as e:
        db.rollback()
    finally:
        db.close()

XAI_API_KEY = os.getenv("XAI_API_KEY", "")
client = OpenAI(api_key=XAI_API_KEY or "placeholder", base_url="https://api.x.ai/v1")

class RegisterRequest(BaseModel):
    name: str
    email: str
    password: str
    department: str
    designation: str
    cadre: Optional[str] = "Indian Statistical Service (ISS)"

class LoginRequest(BaseModel):
    email: str
    password: str

@app.get("/")
def health_check(db: Session = Depends(get_db)):
    return {
        "status": "online",
        "users_count": db.query(UserRecord).count(),
        "quizzes_count": db.query(TopicQuizRecord).count()
    }

@app.post("/api/register")
def register(req: RegisterRequest, db: Session = Depends(get_db)):
    clean_email = req.email.strip().lower()
    existing = db.query(UserRecord).filter(UserRecord.email == clean_email).first()
    if existing:
        raise HTTPException(status_code=400, detail="User already registered with this email.")
    
    user = UserRecord(
        name=req.name.strip(),
        email=clean_email,
        password=req.password.strip(),
        department=req.department.strip(),
        designation=req.designation.strip(),
        cadre=req.cadre.strip() if req.cadre else "Indian Statistical Service (ISS)",
        role="admin" if clean_email == "123@gov.ac.in" else "employee",
        competency_score="75%",
        posh_status="Pending"
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return {"status": "success", "user": {"id": user.id, "name": user.name, "email": user.email, "department": user.department, "designation": user.designation, "cadre": user.cadre, "role": user.role, "competency_score": user.competency_score, "posh_status": user.posh_status}}

@app.post("/api/login")
def login(req: LoginRequest, db: Session = Depends(get_db)):
    clean_email = req.email.strip().lower()
    user = db.query(UserRecord).filter(UserRecord.email == clean_email).first()
    if not user or user.password != req.password.strip():
        raise HTTPException(status_code=401, detail="Invalid email or password.")
    return {"id": user.id, "name": user.name, "email": user.email, "department": user.department, "designation": user.designation, "cadre": user.cadre, "role": user.role, "competency_score": user.competency_score, "posh_status": user.posh_status}

@app.get("/api/admin/users")
def get_users(db: Session = Depends(get_db)):
    users = db.query(UserRecord).all()
    return [{"id": u.id, "name": u.name, "email": u.email, "department": u.department, "designation": u.designation, "cadre": u.cadre, "role": u.role, "score": u.competency_score, "posh": u.posh_status} for u in users]
