import json
import logging
from datetime import timedelta
from uuid import uuid4

from sqlalchemy import and_, or_, select

from roadeye import models as m
from roadeye.config import settings
from roadeye.db import SessionLocal, now
from roadeye.services import anomalies, emit_next, process_input, require_run

logger = logging.getLogger("roadeye.worker")


def schedule() -> bool:
    with SessionLocal.begin() as db:
        run = db.scalar(
            select(m.Run)
            .where(m.Run.state == "playing")
            .order_by(m.Run.created_at)
            .with_for_update(skip_locked=True)
            .limit(1)
        )
        if not run:
            return False
        emit_next(db, run)
        return True


def claim(at=None) -> tuple[str, str] | None:
    at = at or now()
    with SessionLocal.begin() as db:
        job = db.scalar(
            select(m.Job)
            .where(
                or_(
                    and_(m.Job.state == "pending", m.Job.available_at <= at),
                    and_(m.Job.state == "leased", m.Job.lease_until <= at),
                )
            )
            .order_by(m.Job.available_at, m.Job.id)
            .with_for_update(skip_locked=True)
            .limit(1)
        )
        if not job:
            return None
        job.state = "leased"
        job.attempts += 1
        job.lease_until = at + timedelta(seconds=settings.lease_seconds)
        job.lease_token = str(uuid4())
        return job.id, job.lease_token


def handle(job_id: str, token: str) -> bool:
    try:
        with SessionLocal.begin() as db:
            # Consistent lock order: run then job, including controls and processing.
            reference = db.get(m.Job, job_id)
            if reference is None:
                return False
            run = require_run(db, reference.run_id, lock=True)
            job = db.scalar(
                select(m.Job)
                .where(m.Job.id == job_id)
                .with_for_update()
                .execution_options(populate_existing=True)
            )
            if not job or job.state != "leased" or job.lease_token != token:
                return False
            event = db.get(m.InputEvent, job.id)
            assert event is not None
            process_input(db, event)
            job.state = "done"
            job.processed_at = now()
            job.lease_until = None
            job.error = None
            db.flush()
            anomalies(db, run)
        logger.info(json.dumps({"event": "job.done", "job_id": job_id}))
        return True
    except Exception as exc:
        with SessionLocal.begin() as db:
            job = db.scalar(select(m.Job).where(m.Job.id == job_id).with_for_update())
            if job and job.state == "leased" and job.lease_token == token:
                job.state = "poison" if job.attempts >= settings.max_attempts else "pending"
                job.available_at = now() + timedelta(seconds=min(60, 2**job.attempts))
                job.error = f"{type(exc).__name__}: {str(exc)[:240]}"
                job.lease_until = None
        logger.warning(
            json.dumps({"event": "job.failed", "job_id": job_id, "error_type": type(exc).__name__})
        )
        return False


def tick() -> bool:
    scheduled = schedule()
    claimed = claim()
    if claimed:
        handle(*claimed)
    return scheduled or claimed is not None
