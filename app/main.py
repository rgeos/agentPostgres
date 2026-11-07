import asyncio
import logging
import os
import threading
import time
from contextlib import asynccontextmanager

import schedule
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

load_dotenv()

from AgentConsulting import ConsultingAgentManager
from AgentSQL import SQLAgentManager
from AgentSupport import SupportAgentManager
from ScheduledPDFScanner import ScheduledPDFScanner

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def start_cron_schedule(
    trigger_time: str,
    scanners: dict[str, ScheduledPDFScanner],
) -> None:
    """Schedules periodic PDF checks for all registered knowledge agents."""
    for scanner in scanners.values():
        schedule.every().day.at(trigger_time).do(scanner.scan_and_ingest)

    logger.info(
        f"📅 Daily cron watch activated for {len(scanners)} agent(s) at {trigger_time}."
    )

    while True:
        try:
            schedule.run_pending()
        except Exception as e:
            logger.error(f"❌ Error during scheduled PDF scan: {str(e)}")
        time.sleep(60)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initializes agent managers once at startup and runs background PDF scanners."""
    support_manager = SupportAgentManager(
        pdf_dir=os.getenv("SUPPORT_PDF_DIRECTORY", "documentation/support")
    )
    consulting_manager = ConsultingAgentManager(
        pdf_dir=os.getenv("CONSULTING_PDF_DIRECTORY", "documentation/consulting")
    )
    sql_manager = SQLAgentManager()

    app.state.agents = {
        "SQL": sql_manager,
        "Consulting": consulting_manager,
        "Support": support_manager,
    }

    app.state.scanners = {
        "Support": ScheduledPDFScanner(support_manager),
        "Consulting": ScheduledPDFScanner(consulting_manager),
    }

    cron_thread = threading.Thread(
        target=start_cron_schedule,
        kwargs={
            "trigger_time": os.getenv("CRON_START_TIME", "02:00"),
            "scanners": app.state.scanners,
        },
        daemon=True,
    )
    cron_thread.start()

    yield

    logger.info("🛑 Shutting down backend engine services...")


app = FastAPI(title="Air-Gapped Aquila Engine", lifespan=lifespan)


class AgentQuery(BaseModel):
    agent_type: str  # "SQL", "Consulting", or "Support"
    question: str


class SyncRequest(BaseModel):
    agent_type: str = "All"  # "Support", "Consulting", or "All"


@app.post("/query")
async def handle_agent_interaction(payload: AgentQuery):
    manager_instance = app.state.agents.get(payload.agent_type.strip())
    if not manager_instance:
        raise HTTPException(
            status_code=400, detail="Invalid agent selector type configuration."
        )

    try:
        result_content = manager_instance.run(payload.question)
        return {"status": "success", "response": result_content}
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Inference error during class execution pipeline: {str(e)}",
        )


@app.post("/sync")
async def trigger_manual_sync(payload: SyncRequest = SyncRequest()):
    """Manually triggers PDF ingestion and modification sync for one or all knowledge agents."""
    target = payload.agent_type.strip()
    scanners: dict[str, ScheduledPDFScanner] = app.state.scanners

    if target == "All":
        selected_scanners = scanners
    elif target in scanners:
        selected_scanners = {target: scanners[target]}
    else:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid agent_type '{target}'. Choose from: 'Support', 'Consulting', or 'All'.",
        )

    results = {}
    try:
        for agent_name, scanner in selected_scanners.items():
            results[agent_name] = await asyncio.to_thread(scanner.scan_and_ingest)

        return {"status": "success", "sync_results": results}
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Manual synchronization failed: {str(e)}",
        )


@app.get("/debug/health")
async def health_check():
    return {"status": "healthy", "framework": "agno", "architecture": "OOM-Class-Based"}
