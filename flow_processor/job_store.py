import enum
import logging
import time
import uuid

from sqlalchemy import JSON, Column, Enum, String, Text, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.types import Float

from flow_processor.config import DATABASE_URL
from flow_processor.exceptions import FlowAlreadyRunningException

Base = declarative_base()
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine)


class JobState(enum.Enum):
    pending = "pending"
    running = "running"
    finished = "finished"
    stopping = "stopping"


class JobStatus(enum.Enum):
    unknown = "unknown"
    success = "success"
    failed = "failed"
    error = "error"
    exit = "exit"


class Job(Base):
    __tablename__ = "jobs"
    id = Column(String, primary_key=True, index=True)
    meta = Column(JSON, nullable=True)
    result = Column(JSON, nullable=True)
    errors = Column(Text, nullable=True)
    state = Column(Enum(JobState), default=JobState.pending)
    status = Column(Enum(JobStatus), default=JobStatus.unknown)
    start_time = Column(Float, default=time.time)
    end_time = Column(Float, nullable=True)


Base.metadata.create_all(bind=engine)


def create_job(meta=None):
    """Create a new job and return its ID."""
    flow_path = (meta or {}).get("flow_path")
    if flow_path:
        db = SessionLocal()
        from sqlalchemy import cast

        running = (
            db.query(Job)
            .filter(
                Job.state != JobState.finished,
                Job.meta.like(f'%"flow_path": "{flow_path}"%'),
            )
            .first()
        )
        if running:
            db.close()
            raise FlowAlreadyRunningException(
                f"A job for flow '{flow_path}' is already running."
            )
        db.close()
    db = SessionLocal()
    job_id = str(uuid.uuid4())
    job = Job(id=job_id, meta=meta or {}, start_time=time.time())
    db.add(job)
    db.commit()
    db.close()
    return job_id


def get_job(job_id):
    db = SessionLocal()
    job = db.query(Job).filter(Job.id == job_id).first()
    db.close()
    return job


def update_job(job_id, **kwargs):
    db = SessionLocal()
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        db.close()
        return None
    for key, value in kwargs.items():
        setattr(job, key, value)
    db.commit()
    db.close()
    return job


def list_jobs(
    limit=50,
    offset=0,
    state=None,
    status=None,
    start_time_from=None,
    start_time_to=None,
    end_time_from=None,
    end_time_to=None,
):
    db = SessionLocal()
    query = db.query(Job)
    if state:
        query = query.filter(Job.state == state)
    if status:
        query = query.filter(Job.status == status)
    if start_time_from:
        query = query.filter(Job.start_time >= start_time_from)
    if start_time_to:
        query = query.filter(Job.start_time <= start_time_to)
    if end_time_from:
        query = query.filter(Job.end_time >= end_time_from)
    if end_time_to:
        query = query.filter(Job.end_time <= end_time_to)
    jobs = query.order_by(Job.start_time.desc()).offset(offset).limit(limit).all()
    db.close()
    return jobs


def abandon_all_running_jobs():
    """Mark all running jobs as abandoned (state=finished, status=unknown)."""
    logging.info("Abandoning all running jobs due to service restart.")
    db = SessionLocal()
    jobs = db.query(Job).filter(Job.state != JobState.finished ).all()
    now = time.time()
    for job in jobs:
        job.state = JobState.finished
        job.status = JobStatus.unknown
        job.errors = (job.errors or "") + "\nAbandoned due to service restart."
        job.end_time = now
    db.commit()
    db.close()


def delete_jobs_filtered(days=None, status=None, state=None):
    db = SessionLocal()
    query = db.query(Job)
    if days is not None:
        cutoff = time.time() - days * 86400
        query = query.filter(Job.end_time != None, Job.end_time < cutoff)
    if status:
        query = query.filter(Job.status == status)
    if state:
        query = query.filter(Job.state == state)
    deleted = query.delete(synchronize_session=False)
    db.commit()
    db.close()
    return deleted


def delete_job_by_id(job_id):
    db = SessionLocal()
    deleted = db.query(Job).filter(Job.id == job_id).delete()
    db.commit()
    db.close()
    return deleted
