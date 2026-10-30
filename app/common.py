import os

POSTGRES_URL = os.environ.get(
    "DATABASE_URL", "postgres+psycopg2://postgres:postgres@localhost:5432/postgres"
)
OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://ollama:11434")
DEFAULT_MODEL = os.environ.get("LLM_MODEL", "qwen2.5:3b")
PROMPT_PATH_CONSULTING = os.environ.get(
    "PROMPT_PATH_CONSULTING", "prompts/agent_consulting.txt"
)
PROMPT_PATH_SQL = os.environ.get("PROMPT_PATH_SQL", "prompts/agent_sql.txt")
PROMPT_PATH_SUPPORT = os.environ.get("PROMPT_PATH_SUPPORT", "prompts/agent_support.txt")


def get_db_url() -> str:
    return POSTGRES_URL


def get_ollama_host() -> str:
    return OLLAMA_HOST


def get_default_model() -> str:
    return DEFAULT_MODEL


def get_consulting_prompt_path() -> str:
    return PROMPT_PATH_CONSULTING


def get_sql_prompt_path() -> str:
    return PROMPT_PATH_SQL


def get_support_prompt_path() -> str:
    return PROMPT_PATH_SUPPORT

def read_prompt_file(prompt_path: str) -> list[str]:
    with open(prompt_path, "r", encoding="utf-8") as f:
        return [line.rstrip("\n") for line in f]