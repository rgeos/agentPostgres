import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

# Import the loader functions instead of global instances
from AgentSQL import get_sql_agent
from AgentConsulting import get_consulting_agent
from AgentSupport import get_support_agent

app = FastAPI(title="Air-Gapped Agno Engine")


class AgentQuery(BaseModel):
    agent_type: str  # "SQL", "Consulting", or "Support"
    question: str


@app.post("/query")
async def handle_agent_interaction(payload: AgentQuery):
    # Map types directly to the dynamic creation functions
    agent_loaders = {
        "SQL": get_sql_agent,
        "Consulting": get_consulting_agent,
        "Support": get_support_agent
    }

    loader = agent_loaders.get(payload.agent_type.strip())
    if not loader:
        raise HTTPException(status_code=400, detail="Invalid agent selector type configuration.")

    try:
        # Build the agent instance on-demand
        selected_agent = loader()
        response = selected_agent.run(payload.question)
        return {"status": "success", "response": response.content}
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Inference error (Check if model download is still in progress): {str(e)}"
        )


@app.get("/debug/health")
async def health_check():
    return {"status": "healthy", "framework": "agno", "environment": "air-gapped-isolated"}
