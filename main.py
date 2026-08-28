import os
import io
import json
import re
import requests
from datetime import datetime
from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional, List
from sqlalchemy import create_engine, Column, Integer, String, Text, func
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from pypdf import PdfReader

app = FastAPI(title="MoSPI iGOT Central Platform")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"]
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
    department = Column(String(255), default="National Accounts Division (NAD)")
    designation = Column(String(255), default="Deputy Director / Assistant Director (ISS)")
    cadre = Column(String(100), default="Indian Statistical Service (ISS)")
    role = Column(String(50), default="employee")
    competency_score = Column(String(10), default="75%")
    completed_modules = Column(Text, default="[]")

class MockIGOTCentralRegistry(Base):
    __tablename__ = "mock_igot_central_registry"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    officer_email = Column(String(255), unique=True, index=True, nullable=False)
    officer_name = Column(String(255), nullable=False)
    verified_courses_json = Column(Text, default="[]")
    last_completed_at = Column(String(100), nullable=True)

class QuizRecord(Base):
    __tablename__ = "topic_quizzes"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    course_id = Column(Integer, nullable=False, default=1)
    question = Column(Text, nullable=False)
    options_json = Column(Text, nullable=False)
    correct_index = Column(Integer, default=0)
    explanation = Column(Text, default="")

Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class LoginRequest(BaseModel):
    email: str
    password: str

@app.get("/")
def serve_index():
    if os.path.exists("index.html"):
        return FileResponse("index.html")
    return {"status": "online", "platform": "MoSPI iGOT"}

@app.get("/login.html")
def serve_login():
    return FileResponse("login.html") if os.path.exists("login.html") else {"error": "login.html not found"}

@app.get("/dashboard.html")
def serve_dashboard():
    return FileResponse("dashboard.html") if os.path.exists("dashboard.html") else {"error": "dashboard.html not found"}

@app.get("/admin.html")
def serve_admin():
    return FileResponse("admin.html") if os.path.exists("admin.html") else {"error": "admin.html not found"}

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
                "completed_modules": [1, 2, 3]
            }
        }

    user = db.query(UserRecord).filter(func.lower(UserRecord.email) == clean_email).first()
    if not user:
        user = UserRecord(
            name="Cadre Officer",
            email=clean_email,
            password=clean_pass,
            department="National Accounts Division (NAD)",
            designation="Deputy Director / Assistant Director (ISS)",
            cadre="Indian Statistical Service (ISS)",
            role="employee",
            competency_score="75%",
            completed_modules="[1, 2]"
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    completed = json.loads(user.completed_modules) if user.completed_modules else []
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
            "completed_modules": completed
        }
    }

@app.get("/api/admin/users")
def get_users(db: Session = Depends(get_db)):
    users = db.query(UserRecord).all()
    return [{"id": u.id, "name": u.name, "email": u.email, "cadre": u.cadre, "department": u.department, "designation": u.designation, "competency": u.competency_score, "completed_count": len(json.loads(u.completed_modules or "[]"))} for u in users]

@app.get("/api/admin/divisional-heatmap")
def get_heatmap():
    return {
        "status": "success",
        "heatmap": [
            {"division": "National Accounts Division (NAD)", "officers_enrolled": 14, "stat_score": 88.5, "tech_score": 72.0, "gov_score": 90.0, "mgmt_score": 84.0, "critical_lag_domain": "Technical Analytics (Python/GIS)", "max_gap_percentage": 18.0},
            {"division": "Field Operations Division (FOD)", "officers_enrolled": 28, "stat_score": 79.0, "tech_score": 65.5, "gov_score": 85.0, "mgmt_score": 76.0, "critical_lag_domain": "Technical Analytics (Python/GIS)", "max_gap_percentage": 24.5},
            {"division": "Price Statistics Division (PSD)", "officers_enrolled": 9, "stat_score": 92.0, "tech_score": 78.0, "gov_score": 88.0, "mgmt_score": 80.0, "critical_lag_domain": "Digital Governance & DPDP", "max_gap_percentage": 12.0}
        ]
    }
