import os
import time
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from contextlib import asynccontextmanager
import ollama

from Database import DatabaseManager
from viz import VisualizationHelper
from AgentSQL import AgentSQL
from AgentConsulting import AgentConsulting
from AgentSupport import AgentSupport

from PromptWatchdog import watchdog

db_manager = DatabaseManager()

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Verifying internal microservice connectivity configurations...")
    watchdog.start()
    time.sleep(5)
    db_manager.initialize_environment()
    global agent_sql, agent_consulting, agent_support

    # check if the model is present
    target_model = os.getenv("OLLAMA_MODEL", "qwen2.5:3b")
    ollama_host = os.getenv("OLLAMA_HOST", "http:ollama:11434")
    init_client = ollama.Client(host=ollama_host)

    try:
        print(f"[BOOT] Verifying local cache for model: '{target_model}'")
        downloaded_models = init_client.list().get("models", [])
        cached_names = [m.get("model") for m in downloaded_models if "model" in m]

        # Exact match or exact base-tag match validation loop
        if target_model not in cached_names:
            print(f"[BOOT] Model '{target_model}' not found in local cache.")
            print(f"[BOOT] Pulling '{target_model}' from Ollama registry (this may take a few minutes)...")

            # This locks execution thread until the download completes safely
            init_client.pull(model=target_model)
            print(f"[BOOT] Model '{target_model}' successfully pulled and verified.")
        else:
            print(f"[BOOT] Model '{target_model}' verified active in memory cluster cache.")

    except Exception as e:
        print(f"[BOOT WARNING] Failed to automatically audit/pull Ollama models: {e}")
        print("[BOOT WARNING] App initialization proceeding. Container might throw downstream runtime errors.")

    agent_sql = AgentSQL()
    agent_consulting = AgentConsulting()
    agent_support = AgentSupport(pdf_dir_path="./documentation")

    yield
    print("Tearing down API runtime context...")
    watchdog.stop()


agent_sql = None
agent_consulting = None
agent_support = None


app = FastAPI(
    title="Multi-Model Air-Gapped RAG Engine", version="7.0.0", lifespan=lifespan
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


class QueryRequest(BaseModel):
    question: str
    model: str | None = None


class ConsultingRequest(BaseModel):
    question: str
    model: str | None = None


class QueryResponse(BaseModel):
    question: str
    tool_called: bool
    generated_sql: str | None
    answer: str
    visualization: dict | None = None
    execution_time_ms: float
    active_model: str


class SupportRequest(BaseModel):
    question: str
    model: str | None = None


class IntentRouterRequest(BaseModel):
    question: str
    user_role: str
    model: str | None = None


# todo - improve on the dashboard (connect to REDASH)
@app.get("/", response_class=HTMLResponse)
def read_dashboard_root():
    index_path = os.path.join(STATIC_DIR, "index.html")
    with open(index_path, "r", encoding="utf-8") as f:
        return f.read()


@app.get("/debug/health")
def status_check():
    try:
        conn = db_manager.get_admin_connection()
        conn.close()
        db_status = "connected"
    except Exception as e:
        db_status = f"disconnected ({str(e)})"

    available_models = []
    ollama_status = "operational"
    try:
        models_response = agent_sql.client.list()
        if "models" in models_response:
            for model_meta in models_response["models"]:
                if "model" in model_meta:
                    available_models.append(model_meta["model"])
    except Exception as e:
        ollama_status = f"unreachable ({str(e)})"

    return {
        "status": "operational"
        if db_status == "connected" and ollama_status == "operational"
        else "degraded",
        "database": {"status": db_status, "target_schema": agent_sql.target_schema},
        "ollama": {
            "status": ollama_status,
            "active_configured_default": agent_sql.default_model,
            "locally_cached_models": available_models,
        },
    }


@app.get("/debug/prompts")
def inspect_active_prompts():
    """
    Returns the real-time, pre-cached prompt strings currently
    loaded inside the application memory core.
    """
    # Define the exact paths registered by your agents
    target_prompts = {
        "consulting": "prompts/agent_consulting.txt",
        "sql": "prompts/agent_sql.txt",
        "synthesis": "prompts/response_synthesis.txt",
        "support": "prompts/agent_support.txt",
    }

    active_memory_dump = {}
    for agent_key, file_path in target_prompts.items():
        # Fetch the string template directly from the watchdog memory cache
        cached_string = watchdog.get_prompt(file_path)

        active_memory_dump[agent_key] = {
            "source_file": file_path,
            "character_count": len(cached_string),
            "current_template_content": cached_string
            if cached_string
            else "[Empty / Not Loaded Yet]",
        }

    return active_memory_dump


# query agent
@app.post("/ask", response_model=QueryResponse)
def handle_user_prompt(payload: QueryRequest):
    start_time = time.perf_counter()
    try:
        # Pass the user selected override model into the agent runtime loop
        result = agent_sql.run_workflow(payload.question, selected_model=payload.model)

        viz_data = None
        if result.get("raw_db_rows"):
            viz_data = VisualizationHelper.generate_chart_metadata(
                result["raw_db_rows"]
            )

        duration_ms = (time.perf_counter() - start_time) * 1000

        return QueryResponse(
            question=payload.question,
            tool_called=result["tool_called"],
            generated_sql=result["generated_sql"],
            answer=result["answer"],
            visualization=viz_data,
            execution_time_ms=round(duration_ms, 2),
            active_model=result["active_model"],
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Query agent workflow runtime exception: {str(e)}"
        )


# consulting agent
@app.post("/consult")
def handle_consulting_prompt(payload: ConsultingRequest):
    """Processes strategic operations questions against live schema matrices."""
    try:
        result = agent_consulting.run_consulting_pipeline(
            user_question=payload.question, selected_model=payload.model
        )
        return result
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Consulting agent workflow runtime exception: {str(e)}",
        )


# customer support
@app.post("/support")
def handle_support_chat(payload: SupportRequest):
    """Router access point for sandboxed customer support operations."""
    if not payload.question.strip():
        raise HTTPException(status_code=400, detail="Inquiry cannot be blank.")

    result = agent_support._generate_advice(
        customer_question=payload.question, selected_model=payload.model
    )
    return result


@app.post("/agent/collaborate")
def automated_collaboration_entrypoint(payload: IntentRouterRequest):
    """
    Central Orchestrator endpoint that dynamically binds agents
    together based on the frontend selected mode dropdown.
    """
    # Route 1: Consulting Query (AgentConsulting Strategic Engine)
    if payload.user_role == "executive":
        return agent_consulting.run_collaboration(
            user_question=payload.question,
            agent_sql_instance=agent_sql,
            selected_model=payload.model,
        )

    # Route 2: Support Query (AgentSupport Knowledge Fusion)
    elif payload.user_role == "customer":
        return agent_support.run_collaboration(
            customer_question=payload.question,
            agent_sql_instance=agent_sql,
            selected_model=payload.model,
        )

    # Route 3: Regular SQL Query (AgentSQL Baseline Parser)
    return agent_sql.run_workflow(payload.question, selected_model=payload.model)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", 8000)),
        reload=False,
        workers=2,
    )
