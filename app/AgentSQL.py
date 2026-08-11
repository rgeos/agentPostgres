import os
import re
import json
import ollama
from functools import lru_cache
from Database import DatabaseTool, SchemaDiscoverer
from PromptWatchdog import watchdog


# --- GLOBAL STATIC ROUTING CACHE FOR CPU OPTIMIZATION ---
@lru_cache(maxsize=256)
def _cached_llm_sql_call(
    client_host: str, model_name: str, instruction: str, question: str
) -> str:
    """Isolated, hashable worker function that performs the slow Ollama call on CPU."""
    print(f"[CACHE MISS] Querying local LLM process registry for: '{question}'")
    client = ollama.Client(host=client_host)

    # this seed really working???
    try:
        env_seed = int(os.getenv("LLM_SEED", "0"))
    except (TypeError, ValueError):
        env_seed = 0

    response = client.generate(
        model=model_name,
        prompt=f"System rules:\n{instruction}\n\nUser Question: {question}",
        format="json",
        options={
            "temperature": 0.0,
            "num_ctx": 4096,  # Expanded context to safely process JSONB layout structures
            "num_predict": 512,  # Expanded response scope for longer CROSS JOIN queries
            "seed": env_seed,
        },
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
        self.prompt_filepath = os.getenv("SQL_PROMPT_PATH", "prompts/agent_sql.txt")
        self.jsonb_schema_filepath = os.getenv(
            "TRANSACTION_SCHEMA_PATH", "prompts/transaction_schema.txt"
        )

        fallback = (
            "Translate query.\n"
            "SCHEMA:\n{live_schema_context}\n"
            "TABLES:\n{allowed_table_rules}\n"
            'FORMAT:\n{{"sql_query": "..."}}'
        )
        watchdog.register_prompt(
            file_path=self.prompt_filepath,
            required_keys=[
                "live_schema_context",
                "allowed_table_rules",
                "target_schema",
            ],
            fallback_text=fallback,
        )

        jsonb_fallback = (
            "Table: {target_schema}.transactions -> Columns: [id, created_on, information (jsonb)]\n"
            "JSONB ARRAY EXTRACTION RULES:\n"
            "- Never extract lists or arrays using paths like '->> 0', as this discards data rows.\n"
            "- Unpack and expand JSONB arrays into distinct records using a CROSS JOIN LATERAL pattern.\n"
            "- Example template: SELECT t.id, x.product_id FROM {target_schema}.transactions t "
            "CROSS JOIN LATERAL jsonb_to_recordset(t.information->'items') AS x(product_id INT);"
        )
        watchdog.register_prompt(
            file_path=self.jsonb_schema_filepath,
            required_keys=[],
            fallback_text=jsonb_fallback,
        )

    def generate_query(self, user_question: str, model_name: str) -> str | None:
        """Isolated pipeline to extract a valid SQL string, accelerated via static memory caches."""
        live_schema_context = self.discoverer.get_active_schema_documentation()
        jsonb_schema_rules = watchdog.get_prompt(self.jsonb_schema_filepath)

        extended_schema_context = f"{live_schema_context}\n\n{jsonb_schema_rules}"

        allowed_table_rules = ", ".join(
            [f"'{self.target_schema}.{t}'" for t in self.db_tool.allowed_tables]
        )

        template = watchdog.get_prompt(self.prompt_filepath)
        system_instruction = template.format(
            live_schema_context=extended_schema_context,
            allowed_table_rules=allowed_table_rules,
            target_schema=self.target_schema,
        )

        try:
            raw_text = _cached_llm_sql_call(
                client_host=self.ollama_host,
                model_name=model_name,
                instruction=system_instruction,
                question=user_question,
            )

            def clean_extracted_sql(sql_str: str) -> str:
                sql_str = re.sub(
                    r"```(?:sql)?\s*(.*?)\s*```",
                    r"\1",
                    sql_str,
                    flags=re.DOTALL | re.IGNORECASE,
                )
                sql_str = sql_str.replace("\n", " ").replace("\t", " ")
                sql_str = re.sub(r"\s+", " ", sql_str)
                return sql_str.strip()

            try:
                parsed = json.loads(raw_text)
                if parsed.get("sql_query"):
                    return clean_extracted_sql(parsed["sql_query"])
            except json.JSONDecodeError:
                pass

            sql_json_match = re.search(
                r'"sql_query"\s*:\s*"(.*?)"', raw_text, re.DOTALL | re.IGNORECASE
            )
            if sql_json_match:
                extracted_sql = clean_extracted_sql(sql_json_match.group(1))
                if "select" in extracted_sql.lower():
                    return extracted_sql

            markdown_match = re.search(
                r"```(?:sql|json)?\s*(.*?)\s*```", raw_text, re.DOTALL | re.IGNORECASE
            )
            if markdown_match:
                extracted_text = markdown_match.group(1)
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
        self.prompt_filepath = os.getenv(
            "SYNTHESIS_PROMPT_PATH", "prompts/response_synthesis.txt"
        )

    def _load_prompt_template(self) -> str:
        try:
            with open(self.prompt_filepath, "r", encoding="utf-8") as f:
                return f.read()
        except Exception:
            return "Answer using records.\nQUESTION:\n{user_question}\nRECORDS:\n{db_rows_json}"

    def _generate_advice(
        self, user_question: str, db_rows_json: str, model_name: str
    ) -> str:
        template = self._load_prompt_template()
        synthesis_prompt = template.format(
            user_question=user_question, db_rows_json=db_rows_json
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