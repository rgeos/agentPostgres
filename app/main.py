from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

from AgentSQL import SQLAgentManager
from AgentConsulting import ConsultingAgentManager
from AgentSupport import SupportAgentManager

app = FastAPI(title="Air-Gapped Agno Engine")


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
