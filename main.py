import os
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
from sqlalchemy import create_engine, Column, Integer, String, Text
from sqlalchemy.orm import declarative_base, sessionmaker, Session

app = FastAPI(title="MoSPI AI Skill Intelligence Platform")

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
    name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password = Column(String(255), nullable=False)
    department = Column(String(255), default="National Accounts Division (NAD)")
    designation = Column(String(255), default="Deputy Director / Assistant Director (ISS)")
    cadre = Column(String(100), default="Indian Statistical Service (ISS)")
    role = Column(String(50), default="employee")
    competency_score = Column(String(10), default="75%")
    posh_status = Column(String(50), default="Pending")

try:
    Base.metadata.create_all(bind=engine)
except Exception as e:
    print(f"Table sync notice: {e}")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class RegisterRequest(BaseModel):
    name: str
    email: str
    password: str
    department: Optional[str] = "National Accounts Division (NAD)"
    designation: Optional[str] = "Deputy Director / Assistant Director (ISS)"
    cadre: Optional[str] = "Indian Statistical Service (ISS)"

class LoginRequest(BaseModel):
    email: str
    password: str

@app.get("/")
def read_root(db: Session = Depends(get_db)):
    try:
        count = db.query(UserRecord).count()
        db_status = "connected"
    except Exception as e:
        count = -1
        db_status = f"error: {str(e)}"
    return {
        "status": "online",
        "database_engine": "PostgreSQL" if "postgresql" in DATABASE_URL else "SQLite",
        "database_status": db_status,
        "users_count": count
    }

@app.post("/api/register")
def register(req: RegisterRequest, db: Session = Depends(get_db)):
    clean_email = req.email.strip().lower()
    try:
        existing = db.query(UserRecord).filter(UserRecord.email == clean_email).first()
        if existing:
            raise HTTPException(status_code=400, detail="Officer already registered.")
        
        user = UserRecord(
            name=req.name.strip(),
            email=clean_email,
            password=req.password.strip(),
            department=req.department.strip() if req.department else "National Accounts Division (NAD)",
            designation=req.designation.strip() if req.designation else "Deputy Director / Assistant Director (ISS)",
            cadre=req.cadre.strip() if req.cadre else "Indian Statistical Service (ISS)",
            role="admin" if clean_email == "123@gov.ac.in" else "employee",
            competency_score="75%",
            posh_status="Pending"
        )
        db.add(user)
        db.commit()
        db.refresh(user)
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
                "posh_status": user.posh_status
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Database sync failed: {str(e)}")

@app.post("/api/login")
def login(req: LoginRequest, db: Session = Depends(get_db)):
    clean_email = req.email.strip().lower()
    user = db.query(UserRecord).filter(UserRecord.email == clean_email).first()
    if not user or user.password != req.password.strip():
        raise HTTPException(status_code=401, detail="Invalid email or password.")
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
            "posh_status": user.posh_status
        }
    }

@app.get("/api/admin/users")
def get_all_users(db: Session = Depends(get_db)):
    users = db.query(UserRecord).all()
    return [{
        "id": u.id,
        "name": u.name,
        "email": u.email,
        "cadre": u.cadre,
        "designation": u.designation,
        "department": u.department,
        "competency": u.competency_score,
        "posh": u.posh_status,
        "role": u.role
    } for u in users]
