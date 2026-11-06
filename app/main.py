import os
import time
import logging
import threading
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv
import schedule

load_dotenv()

from AgentSQL import SQLAgentManager
from AgentConsulting import ConsultingAgentManager
from AgentSupport import SupportAgentManager
from ScheduledPDFScanner import ScheduledPDFScanner

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def start_cron_schedule(
    trigger_time: str = "02:00", pdf_directory: str = "documentation"
):
    """
    Initialises the manager and schedules a daily scan.

    :param pdf_directory:
    :param trigger_time: String in 24-hour format "HH:MM" (e.g., "02:00" for 2 AM)
    """
    manager = SupportAgentManager(pdf_dir=pdf_directory)
    scanner = ScheduledPDFScanner(manager)

    schedule.every().day.at(trigger_time).do(scanner.scan_and_ingest)

    logger.info(
        f"📅 Daily cron watch activated. Scheduled to run every day at {trigger_time}."
    )

    try:
        while True:
            schedule.run_pending()
            time.sleep(60)
    except Exception as e:
        logger.error(f"❌ Critical failure in background cron loop: {str(e)}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI Lifespan context manager to handle startup background tasks safely."""
    cron_thread = threading.Thread(
        target=start_cron_schedule,
        kwargs={
            "trigger_time": os.getenv("CRON_START_TIME", "20:28"),
            "pdf_directory": os.getenv("PDF_DIRECTORY", "documentation"),
        },
        daemon=True,
    )
    cron_thread.start()

    yield  # API handles requests here

    logger.info("🛑 Shutting down backend engine services...")


app = FastAPI(title="Air-Gapped Aquila Engine", lifespan=lifespan)


class AgentQuery(BaseModel):
    agent_type: str  # "SQL", "Consulting", or "Support"
    question: str


@app.post("/query")
async def handle_agent_interaction(payload: AgentQuery):
    agent_class_map = {
        "SQL": SQLAgentManager,
        "Consulting": ConsultingAgentManager,
        "Support": SupportAgentManager,
    }

    TargetClass = agent_class_map.get(payload.agent_type.strip())
    if not TargetClass:
        raise HTTPException(
            status_code=400, detail="Invalid agent selector type configuration."
        )

    try:
        manager_instance = TargetClass()
        result_content = manager_instance.run(payload.question)
        return {"status": "success", "response": result_content}
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Inference error during class execution pipeline: {str(e)}",
        )


@app.get("/debug/health")
async def health_check():
    return {"status": "healthy", "framework": "agno", "architecture": "OOM-Class-Based"}
