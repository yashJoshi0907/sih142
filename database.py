"""
database.py — SQLAlchemy ORM for SIH26142
Swap DBMS by setting the DATABASE_URL environment variable:
  SQLite     (default): sqlite:///./sih142.db
  PostgreSQL:           postgresql://user:pass@localhost/sih142
  MySQL:                mysql+pymysql://user:pass@localhost/sih142
"""
import os
from datetime import datetime
from typing import Optional, List

from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, ForeignKey, Text
from sqlalchemy.orm import declarative_base, sessionmaker, relationship, Session

# ─── Connection ───────────────────────────────────────────────────────────────
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./sih142.db")

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {},
    echo=False,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# ─── Models ───────────────────────────────────────────────────────────────────
class ProcessingJob(Base):
    __tablename__ = "processing_jobs"

    id           = Column(Integer, primary_key=True, index=True)
    filename     = Column(String(256), nullable=False)
    status       = Column(String(32), default="queued")   # queued | running | done | failed
    sr_model     = Column(String(64), nullable=False)
    scale_factor = Column(Float, default=2.0)
    input_path   = Column(String(512))
    output_path  = Column(String(512))
    error_msg    = Column(Text, nullable=True)
    created_at   = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    metrics = relationship("MetricsResult", back_populates="job", uselist=False, cascade="all, delete-orphan")


class MetricsResult(Base):
    __tablename__ = "metrics_results"

    id                  = Column(Integer, primary_key=True, index=True)
    job_id              = Column(Integer, ForeignKey("processing_jobs.id"), nullable=False)
    psnr_vs_bicubic     = Column(Float, nullable=True)
    ssim_vs_bicubic     = Column(Float, nullable=True)
    inference_time_sec  = Column(Float, nullable=True)
    input_resolution_m  = Column(Float, default=10.0)
    output_resolution_m = Column(Float, nullable=True)
    hallucination_score = Column(Float, nullable=True)   # lower = more physically consistent

    job = relationship("ProcessingJob", back_populates="metrics")


# ─── Init ─────────────────────────────────────────────────────────────────────
def init_db():
    """Create all tables. Call once at app startup."""
    Base.metadata.create_all(bind=engine)


def get_db():
    """Dependency-injection style session factory."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ─── Repositories ─────────────────────────────────────────────────────────────
class JobRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, filename: str, sr_model: str, scale_factor: float,
               input_path: str) -> ProcessingJob:
        job = ProcessingJob(
            filename=filename,
            sr_model=sr_model,
            scale_factor=scale_factor,
            input_path=input_path,
            status="queued",
        )
        self.db.add(job)
        self.db.commit()
        self.db.refresh(job)
        return job

    def get(self, job_id: int) -> Optional[ProcessingJob]:
        return self.db.query(ProcessingJob).filter(ProcessingJob.id == job_id).first()

    def list_all(self, limit: int = 50) -> List[ProcessingJob]:
        return (
            self.db.query(ProcessingJob)
            .order_by(ProcessingJob.created_at.desc())
            .limit(limit)
            .all()
        )

    def update_status(self, job_id: int, status: str,
                      output_path: str = None, error_msg: str = None):
        job = self.get(job_id)
        if job:
            job.status = status
            if output_path:
                job.output_path = output_path
            if error_msg:
                job.error_msg = error_msg
            if status in ("done", "failed"):
                job.completed_at = datetime.utcnow()
            self.db.commit()

    def delete(self, job_id: int):
        job = self.get(job_id)
        if job:
            self.db.delete(job)
            self.db.commit()


class MetricsRepository:
    def __init__(self, db: Session):
        self.db = db

    def save(self, job_id: int, psnr: float, ssim: float,
             inference_time: float, output_res_m: float,
             hallucination_score: float = None) -> MetricsResult:
        m = MetricsResult(
            job_id=job_id,
            psnr_vs_bicubic=psnr,
            ssim_vs_bicubic=ssim,
            inference_time_sec=inference_time,
            output_resolution_m=output_res_m,
            hallucination_score=hallucination_score,
        )
        self.db.add(m)
        self.db.commit()
        self.db.refresh(m)
        return m

    def get_by_job(self, job_id: int) -> Optional[MetricsResult]:
        return self.db.query(MetricsResult).filter(MetricsResult.job_id == job_id).first()

    def list_all(self) -> List[MetricsResult]:
        return self.db.query(MetricsResult).all()
