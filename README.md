# Multi-Model Air-Gapped RAG Engine

My first attempt at containerized Multi-Agent Retrieval-Augmented Generation (RAG) system.  
The application coordinates specialized local LLM microservices to securely query structured databases (PostgreSQL/pgvector) 
and extract text from unstructured documents (PDFs), all running fully offline on local hardware (on CPU).

---

## 🏗️ Architecture & Agent Core
The application splits distinct analytical reasoning domains into decoupled, cooperative agents:

*   **AgentSQL**: Single-purpose class that translates raw natural language inquiries into SQL statements (sometimes not that smart).
It features automated schema parsing and hardcoded template rules to properly unpack JSONB data arrays via `CROSS JOIN LATERAL` sets.
*   **AgentConsulting**: Synthesizes high-level corporate strategies and metrics based directly on rows extracted from live database schema tables.
*   **AgentSupport**: Handles client-facing document lookups. It automatically indexes, extracts, and searches local context from PDF manuals alongside dedicated tables.
*   **PromptWatchdog**: An asynchronous, thread-safe, non-blocking monitoring engine that pre-caches active configurations and performs hot-reloads on live prompt adjustments without interrupting runtime loops.

---

## 🛠️ Prerequisites
Before running the application, make sure your host machine has the following tools installed:
*   [Docker](https://docker.com)
*   [Docker Compose](https://docker.com)

---

## 📦 Installation & Setup

### 1. Project Directory Structure
Ensure your app components are laid out relative to your root compose footprint:
```text
.
├── docker-compose.yml
├── .env
└── app/
    ├── main.py
    ├── AgentSQL.py
    ├── AgentConsulting.py
    ├── AgentSupport.py
    ├── Database.py
    ├── viz.py
    ├── PromptWatchdog.py
    ├── requirements.txt
    ├── documentation/     # Place client manuals & PDFs here
    └── prompts/           # Core prompt templates path
```

### 2. Configure Environment Variables
Create a file named `.env` in the root directory. Paste and fill out the configuration block below:

```ini
# Database Core Configurations
DB_HOST=db_host
DB_PORT=5432
DB_NAME=db_name
DB_USER=db_user
DB_PASSWORD=db_password

# Restricted Database Read-Only Access
TARGET_SCHEMA=isolated_analytics_schema
LLM_READER_USER=llm_reader
LLM_READER_PASSWORD=llm_password
ALLOWED_TABLES=orders,products,transactions

# Ollama Engine Settings
OLLAMA_HOST=http://ollama:11434
OLLAMA_MODEL=qwen2.5:3b
OLLAMA_NUM_PARALLEL=2
LLM_SEED=42

# Operational System Settings
HOST=0.0.0.0
PORT=8000
```

---

## 🚀 Running the Application

### Step 1: Fire up the Containers
Run the Docker Compose command to build out the images and spawn the background services:
```bash
docker compose up -d
```
*Note: During the very first build process, the application will automatically call the Ollama registry API to fetch your configured default model (`qwen2.5:3b`).  
This might take a few minutes depending on your internet connection speed.*

### Step 2: Verify Service Health
Check if your data schemas, read-only permissions, and models were initialized correctly:
```bash
curl http://<host_URL_or_IP_address>:8000/debug/health
```

---

## 🔌 API Documentation & Usage

- Access the application from the UI at `http://<host_URL_or_IP_address>:8000/`
- Select the type of agent you want to interact with (Eg: SQL, Support, Consulting)
- Select the LLM model
- Type your question into the query box:
   - (Consulting): What should I do to reduce my products stock based on the current orders?
   - (Support): Where is each and every product imported from?
   - (SQL): What products do we have in the stock and what is the volume of each type of product?

### Inspect Live Cache Templates (`/debug/prompts`)
Exposes live memory-mapped text shapes monitored by the Prompt Watchdog engine.
```bash
curl http://<host_URL_or_IP_address>:8000/debug/prompts`
```

---

## 🔒 Security & Data Guardrails
*   **Zero Leakage**: All computation loops take place within an air-gapped container context. No metrics are shipped outside the infrastructure borders.
*   **Transactional Isolation**: The application drops system admin context immediately after the initialization phase. 
The processing engine routes all queries exclusively through a restricted user profile (`LLM_READER_USER`) with selective `GRANT SELECT` layout privileges.
*   **Keyword Interception**: The `DatabaseTool` validates string buffers against forbidden execution sequences (`DROP`, `DELETE`, `TRUNCATE`, `ALTER`, etc.)
and halts unsafe pipeline calls natively before hitting database tables.
