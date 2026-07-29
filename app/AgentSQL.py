import os
import re
import json
import ollama
from functools import lru_cache
from database import DatabaseTool, SchemaDiscoverer


# --- GLOBAL STATIC ROUTING CACHE FOR CPU OPTIMIZATION ---
# Cache up to 256 unique natural language questions independently of class mutation states.
# This prevents 'self' mutating elements from triggering unhashable type runtime errors.
@lru_cache(maxsize=256)
def _cached_llm_sql_call(
    client_host: str, model_name: str, instruction: str, question: str
) -> str:
    """Isolated, hashable worker function that performs the slow Ollama call on CPU."""
    print(f"[CACHE MISS] Querying local LLM process registry for: '{question}'")
    client = ollama.Client(host=client_host)
    response = client.generate(
        model=model_name,
        prompt=f"System rules:\n{instruction}\n\nUser Question: {question}",
        format="json",
        options={"temperature": 0.0, "num_ctx": 2048, "num_predict": 256},
    )
    return response["response"].strip()


class SQLGenerationAgent:
    """Single Purpose Class: Translates natural questions into strict, clean SQL queries only."""

    def __init__(self, client: ollama.Client, target_schema: str):
        self.client = client
        self.ollama_host = os.getenv("OLLAMA_HOST", "http://ollama:11434")
        self.target_schema = target_schema
        self.discoverer = SchemaDiscoverer()
        self.db_tool = DatabaseTool()

    def generate_query(self, user_question: str, model_name: str) -> str | None:
        """Isolated pipeline to extract a valid SQL string, accelerated via static memory caches."""
        live_schema_context = self.discoverer.get_active_schema_documentation()

        allowed_table_rules = ", ".join(
            [f"'{self.target_schema}.{t}'" for t in self.db_tool.allowed_tables]
        )

        system_instruction = (
            f"You are a machine translator. Translate the user query into a single valid PostgreSQL SELECT statement.\n\n"
            f"DATABASE SCHEMA MATRIX:\n"
            f"{live_schema_context}\n\n"
            f"RULES:\n"
            f"- Use standard SQL tools where appropriate (e.g., SUM, COUNT, AVG, JOIN).\n"
            f"- You are ALLOWED and encouraged to use JOIN clauses to connect records from multiple tables if needed.\n"
            f"- Never write a 'GROUP BY id' clause.\n"
            f"- You can ONLY query tables matching this prefix checklist: [{allowed_table_rules}]. Do not reference any other tables.\n\n"
            f"Include corresponding descriptive columns (like 'name' or titles) in your SELECT clause "
            f"so the application can properly visualize the combined data data arrays.\n\n"
            f"OUTPUT FORMAT:\n"
            f"You must output a raw JSON object matching exactly this structure, with no commentary:\n"
            f'{{"sql_query": "SELECT ... FROM {self.target_schema}.products JOIN {self.target_schema}.<other_allowed_table> ..."}}'
        )

        try:
            # Route execution down through the hashable cache validator wrapper
            raw_text = _cached_llm_sql_call(
                client_host=self.ollama_host,
                model_name=model_name,
                instruction=system_instruction,
                question=user_question,
            )

            # Helper function to normalize text (remove markdown blocks, replace extra spaces, flatten newlines)
            def clean_extracted_sql(sql_str: str) -> str:
                # Remove nested markdown code blocks if present
                sql_str = re.sub(
                    r"```(?:sql)?\s*(.*?)\s*```",
                    r"\1",
                    sql_str,
                    flags=re.DOTALL | re.IGNORECASE,
                )
                # Replace escaped quotes, internal newlines, or tabs with simple spaces
                sql_str = (
                    sql_str.replace('\\"', '"').replace("\n", " ").replace("\t", " ")
                )
                # Collapse multiple continuous spaces into one
                sql_str = re.sub(r"\s+", " ", sql_str)
                return sql_str.strip()

            # Stage 1: Try decoding the entire response as a direct JSON string map
            try:
                parsed = json.loads(raw_text)
                if parsed.get("sql_query"):
                    return clean_extracted_sql(parsed["sql_query"])
            except json.JSONDecodeError:
                pass

            # Stage 2: Robust regex to extract whatever value sits inside the "sql_query" key
            sql_json_match = re.search(
                r'"sql_query"\s*:\s*"(.*?)"', raw_text, re.DOTALL | re.IGNORECASE
            )
            if sql_json_match:
                extracted_sql = clean_extracted_sql(sql_json_match.group(1))
                if "select" in extracted_sql.lower():
                    return extracted_sql

            # Stage 3: Look for raw SQL inside markdown code fence blocks anywhere in the text
            markdown_match = re.search(
                r"```(?:sql|json)?\s*(.*?)\s*```", raw_text, re.DOTALL | re.IGNORECASE
            )
            if markdown_match:
                extracted_text = markdown_match.group(1)
                # Check if there is an inner JSON string pattern
                inner_json = re.search(
                    r'"sql_query"\s*:\s*"(.*?)"', extracted_text, re.DOTALL
                )
                if inner_json:
                    return clean_extracted_sql(inner_json.group(1))

                extracted_text = clean_extracted_sql(extracted_text)
                if (
                    "select" in extracted_text.lower()
                    and "from" in extracted_text.lower()
                ):
                    return extracted_text

            # Stage 4: Absolute fallback line scan
            clean_text = re.sub(r"[\{\}\[\]]", "", raw_text)
            sql_match = re.search(
                r"(?i)\b(SELECT\s+.+?\s+FROM\s+.+?)(?:;|$)", clean_text, re.DOTALL
            )
            if sql_match:
                return clean_extracted_sql(sql_match.group(1))

            return None
        except Exception as e:
            print(f"[SQL AGENT ERROR] Translation execution failure: {e}")
            return None


class ResponseSynthesisAgent:
    """Compiles final human answers using custom active models based strictly on data."""

    def __init__(self, client: ollama.Client):
        self.client = client

    def _generate_advice(
        self, user_question: str, db_rows_json: str, model_name: str
    ) -> str:
        synthesis_prompt = (
            f"You are a factual reporting clerk. Answer the user's question using ONLY the provided database rows.\n\n"
            f"User Question: '{user_question}'\n"
            f"Factual Database Records (JSON format):\n{db_rows_json}\n\n"
            f"INSTRUCTIONS:\n"
            f"1. Summarise these database records into a direct, friendly natural language response.\n"
            f"2. Your answer must align 100% with the numbers and names listed in the records above.\n"
            f"3. Do not invent details, hallucinate items, or refer to any tables or SQL syntax structures."
        )

        try:
            response = self.client.generate(
                model=model_name,
                prompt=synthesis_prompt,
                options={"temperature": 0.0, "num_ctx": 2048, "num_predict": 256},
            )
            return response["response"]
        except Exception as e:
            return f"Error synthesising response context block: {str(e)}"


class AgentSQL:
    """Orchestrator Class: Directs the contextual payload path across decoupled model instances."""

    def __init__(self):
        ollama_host = os.getenv("OLLAMA_HOST", "http://ollama:11434")
        self.client = ollama.Client(host=ollama_host)
        self.default_model = os.getenv("OLLAMA_MODEL", "qwen2.5:3b-instruct-q4_K_M")
        self.target_schema = os.getenv("TARGET_SCHEMA", "public_read_only")
        self.db_tool = DatabaseTool()

        self.sql_generation_worker = SQLGenerationAgent(self.client, self.target_schema)
        self.synthesis_worker = ResponseSynthesisAgent(self.client)

    def run_workflow(
        self, user_question: str, selected_model: str | None = None
    ) -> dict:
        """Runs the multi-agent pipeline using either the user-selected or default model target."""
        active_model = selected_model if selected_model else self.default_model
        print(
            f"[ORCHESTRATOR] Initializing execution pipeline targeting model: '{active_model}'"
        )

        generated_sql = self.sql_generation_worker.generate_query(
            user_question, model_name=active_model
        )

        if not generated_sql or not generated_sql.strip().lower().startswith("select"):
            return {
                "tool_called": False,
                "generated_sql": generated_sql,
                "answer": f"I am sorry, but the model '{active_model}' couldn't formulate a secure database query.",
                "raw_db_rows": None,
                "active_model": active_model,
            }

        try:
            tool_output_parsed = self.db_tool.execute_read_query_raw(generated_sql)
        except Exception as e:
            return {
                "tool_called": True,
                "generated_sql": generated_sql,
                "answer": f"Database execution halted due to system permissions rules: {str(e)}",
                "raw_db_rows": None,
                "active_model": active_model,
            }

        if len(tool_output_parsed) == 0:
            return {
                "tool_called": True,
                "generated_sql": generated_sql,
                "answer": f"No records found in the database matching your request for '{user_question}'.",
                "raw_db_rows": [],
                "active_model": active_model,
            }

        clean_json_payload = json.dumps(tool_output_parsed)
        final_answer = self.synthesis_worker._generate_advice(
            user_question, clean_json_payload, model_name=active_model
        )

        return {
            "tool_called": True,
            "generated_sql": generated_sql,
            "answer": final_answer,
            "raw_db_rows": tool_output_parsed,
            "active_model": active_model,
        }
