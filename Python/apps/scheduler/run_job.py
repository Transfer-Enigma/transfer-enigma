#!/usr/bin/env python3
import argparse
import asyncio
import importlib
import logging
import sys
from datetime import datetime

from module_shared.config import get_settings
from module_shared.database import get_database
from module_shared.logger import setup_logging
from module_shared.schemas.job_log import JobLogModel

logger = logging.getLogger("scheduler.run_job")


async def _run():
    parser = argparse.ArgumentParser(description="Transfer Enigma Task Scheduler")
    parser.add_argument("--job-name", required=True, help="Unique job identifier")
    args = parser.parse_args()

    job_name = args.job_name
    settings = get_settings()
    setup_logging("scheduler", default_level=settings.LOG_LEVEL)

    logger.info("Starting job: %s", job_name)

    db = get_database()
    log_id = None

    try:
        async with db.session_context() as session:
            entry = JobLogModel(
                job_name=job_name,
                status="in_progress",
                started_at=datetime.utcnow(),
            )
            session.add(entry)
            await session.flush()
            log_id = entry.id
        logger.info("Job log entry created: id=%s, status=in_progress", log_id)
    except Exception as e:
        logger.exception("Cannot create job log entry in DB: %s", e)
        sys.exit(1)

    try:
        module = importlib.import_module(f"scheduler.jobs.{job_name}")
        await module.main()
    except Exception as e:
        logger.exception("Job '%s' FAILED: %s", job_name, e)
        status = "error"
        error_message = str(e)
    else:
        logger.info("Job '%s' completed successfully", job_name)
        status = "completed"
        error_message = None

    try:
        async with db.session_context() as session:
            entry = await session.get(JobLogModel, log_id)
            if entry is not None:
                entry.status = status
                entry.error_message = error_message
                entry.finished_at = datetime.utcnow()
        logger.info("Job log entry updated: id=%s, status=%s", log_id, status)
    except Exception as e:
        logger.exception("Cannot update job log entry in DB: %s", e)

    if status == "error":
        sys.exit(1)


def main():
    asyncio.run(_run())


if __name__ == "__main__":
    main()
