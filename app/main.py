import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from AgentSQL import AgentSQL
from AgentConsulting import AgentConsulting
from AgentSupport import AgentSupport

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("AquilaOrchestrator")

sql_service = None
consulting_service = None
support_service = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global sql_service, consulting_service, support_service
    logger.info("Spawning Aquila microservices ...")

    sql_service = AgentSQL()
    consulting_service = AgentConsulting()
    support_service = AgentSupport()
    logger.info(f"Aquila microservices started ...")

    yield
    logger.info(f"Aquila microservices stopped ...")


app = FastAPI(title="Aquila Orchestrator", lifespan=lifespan)


class QueryPayload(BaseModel):
    agent_type: str
    message: str


@app.post("/query")
async def process_incoming_query(payload: QueryPayload):
    target = payload.agent_type.lower()

    try:
        if target == "sql":
            output = sql_service.run(payload.message)
        elif target == "consulting":
            output = consulting_service.run(payload.message)
        elif target == "support":
            output = support_service.run(payload.message)
        else:
            raise HTTPException(
                status_code=400, detail=f"{payload.agent_type}: Invalid agent type"
            )

        return {"content": output}

    except Exception as e:
        logger.error(f"Execution failed: {str(e)}")
