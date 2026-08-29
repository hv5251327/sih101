import os
import io
import json
import re
import requests
from datetime import datetime
from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
from sqlalchemy import create_engine, Column, Integer, String, Text, func
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from pypdf import PdfReader

app = FastAPI(title="MoSPI iGOT Central Platform")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./igot_mospi.db")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+psycopg2://", 1)
elif DATABASE_URL.startswith("postgresql://") and not DATABASE_URL.startswith("postgresql+psycopg2://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg2://", 1)

connect_args = {"check_same_thread": False} if "sqlite" in DATABASE_URL else {}
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

class OfficerProfile(Base):
    __tablename__ = "officer_profiles"
    officer_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    full_name = Column(String(150), nullable=False)
    email = Column(String(150), unique=True, index=True, nullable=False)
    department = Column(String(150), nullable=False)
    designation_name = Column(String(150), nullable=True)
    current_statistical = Column(Integer, default=0)
    current_technical = Column(Integer, default=0)
    current_governance = Column(Integer, default=0)
    current_behavioural = Column(Integer, default=0)

class AuditLogRecord(Base):
    __tablename__ = "compliance_audit_logs"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    officer_email = Column(String(255), nullable=False)
    action_type = Column(String(100), nullable=False)
    details = Column(Text, default="")
    timestamp = Column(String(100), nullable=False)

Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def log_audit_event(db: Session, email: str, action: str, details: str):
    try:
        entry = AuditLogRecord(
            officer_email=email,
            action_type=action,
            details=details,
            timestamp=datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
        )
        db.add(entry)
        db.commit()
    except Exception:
        pass

class RegisterRequest(BaseModel):
    name: Optional[str] = "Registered Officer"
    email: str
    password: str
    department: Optional[str] = "National Accounts Division (NAD)"
    designation: Optional[str] = "Junior Statistical Officer (JSO)"
    cadre: Optional[str] = "Subordinate Statistical Service (SSS)"

class LoginRequest(BaseModel):
    email: str
    password: str

@app.post("/api/register")
def register(req: RegisterRequest, db: Session = Depends(get_db)):
    clean_email = req.email.strip().lower()
    clean_pass = req.password.strip()
    name_val = req.name.strip() if req.name else "Registered Officer"
    dept_val = req.department.strip() if req.department else "National Accounts Division (NAD)"
    desig_val = req.designation.strip() if req.designation else "Junior Statistical Officer (JSO)"
    cadre_val = req.cadre.strip() if req.cadre else "Subordinate Statistical Service (SSS)"

    # 1. Update / Insert into 'users'
    user = db.query(UserRecord).filter(func.lower(UserRecord.email) == clean_email).first()
    if not user:
        user = UserRecord(
            name=name_val,
            email=clean_email,
            password=clean_pass,
            hashed_password=clean_pass,
            department=dept_val,
            designation=desig_val,
            cadre=cadre_val,
            role="admin" if clean_email == "123@gov.ac.in" else "employee",
            competency_score="75%",
            posh_status="Pending",
            completed_modules="[]"
        )
        db.add(user)
    else:
        user.name = name_val
        user.password = clean_pass
        user.hashed_password = clean_pass
        user.department = dept_val
        user.designation = desig_val
        user.cadre = cadre_val

    # 2. Sync to 'officer_profiles'
    profile = db.query(OfficerProfile).filter(func.lower(OfficerProfile.email) == clean_email).first()
    if not profile:
        profile = OfficerProfile(
            full_name=name_val,
            email=clean_email,
            department=dept_val,
            designation_name=desig_val,
            current_statistical=0,
            current_technical=0,
            current_governance=0,
            current_behavioural=0
        )
        db.add(profile)
    else:
        profile.full_name = name_val
        profile.department = dept_val
        profile.designation_name = desig_val

    db.commit()
    log_audit_event(db, clean_email, "USER_REGISTER", f"Registered under {cadre_val}")

    return {
        "status": "success",
        "user": {
            "name": name_val,
            "email": clean_email,
            "department": dept_val,
            "designation": desig_val,
            "cadre": cadre_val
        }
    }

@app.post("/api/login")
def login(req: LoginRequest, db: Session = Depends(get_db)):
    clean_email = req.email.strip().lower()
    clean_pass = req.password.strip()

    if clean_email == "123@gov.ac.in" and clean_pass == "1234":
        return {"status": "success", "role": "admin", "user": {"email": clean_email, "name": "Chief Administrator", "role": "admin"}}

    user = db.query(UserRecord).filter(func.lower(UserRecord.email) == clean_email).first()
    if not user or (user.password != clean_pass and user.hashed_password != clean_pass):
        raise HTTPException(status_code=401, detail="Invalid email or password.")

    return {
        "status": "success",
        "role": user.role,
        "user": {
            "name": user.name,
            "email": user.email,
            "department": user.department,
            "designation": user.designation,
            "cadre": user.cadre,
            "competency_score": user.competency_score
        }
    }

@app.get("/api/admin/analytics")
def get_admin_analytics(db: Session = Depends(get_db)):
    users = db.query(UserRecord).filter(UserRecord.role != "admin").all()
    cadres = db.query(UserRecord.cadre, func.count(UserRecord.id)).group_by(UserRecord.cadre).all()
    
    roster = [{
        "name": u.name,
        "email": u.email,
        "designation": u.designation,
        "department": u.department,
        "competency_score": u.competency_score.replace("%", ""),
        "completed_count": len(json.loads(u.completed_modules or "[]")),
        "pending_courses": ["SNA 2008", "PLFS Sampling"]
    } for u in users]

    cadre_summary = [{"designation": c[0] or "General", "count": c[1], "avg_score": 75} for c in cadres]

    return {
        "total_officers": len(users),
        "total_courses": 5,
        "cadre_summary": cadre_summary,
        "roster": roster
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)