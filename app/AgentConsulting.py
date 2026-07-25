import os
import json
import ollama
from database import DatabaseTool, SchemaDiscoverer, DecimalEncoder
from AgentSQL import SQLGenerationAgent


class AgentConsulting:
    def __init__(self):
        ollama_host = os.getenv("OLLAMA_HOST", "http://ollama:11434")
        self.client = ollama.Client(host=ollama_host)
        self.default_model = os.getenv("OLLAMA_MODEL", "qwen2.5:3b-instruct-q4_K_M")
        self.target_schema = os.getenv("TARGET_SCHEMA", "public_read_only")

        # Reuse baseline ecosystem tools
        self.db_tool = DatabaseTool()
        self.discoverer = SchemaDiscoverer()
        self.sql_worker = SQLGenerationAgent(self.client, self.target_schema)

    def run_consulting_pipeline(
        self, user_question: str, selected_model: str | None = None
    ) -> dict:
        active_model = selected_model if selected_model else self.default_model
        print(
            f"[CONSULTING AGENT] Initiating workflow under model target: '{active_model}'"
        )

        # Step 1: Generate the underlying PostgreSQL statement
        generated_sql = self.sql_worker.generate_query(
            user_question, model_name=active_model
        )

        # Fallback verification step if SQL validation fails
        if not generated_sql or not generated_sql.strip().lower().startswith("select"):
            return self._format_error_payload(
                active_model,
                generated_sql,
                "Unable to generate a valid data extraction loop for this consulting topic.",
            )

        # Step 2: Extract real-time inventory statistics
        try:
            db_rows = self.db_tool.execute_read_query_raw(generated_sql)
        except Exception as e:
            return self._format_error_payload(
                active_model,
                generated_sql,
                f"Consulting data pipeline blocked by system access limits: {str(e)}",
            )

        # Step 3: Handle empty tables gracefully
        if not db_rows:
            return {
                "success": True,
                "generated_sql": generated_sql,
                "consulting_advice": f"No active catalog parameters match your inquiry. Recommended Next Step: Audit products setup in schema '{self.target_schema}'.",
                "metrics_payload": [],
                "active_model": active_model,
            }

        # Step 4: Synthesize strategic consulting insights
        clean_json_data = json.dumps(db_rows, cls=DecimalEncoder)
        live_schema_context = self.discoverer.get_active_schema_documentation()

        consulting_advice = self._generate_strategic_advice(
            user_question=user_question,
            db_rows_json=clean_json_data,
            schema_context=live_schema_context,
            model_name=active_model,
        )

        return {
            "success": True,
            "generated_sql": generated_sql,
            "consulting_advice": consulting_advice,
            "metrics_payload": db_rows,
            "active_model": active_model,
        }

    def _generate_strategic_advice(
        self,
        user_question: str,
        db_rows_json: str,
        schema_context: str,
        model_name: str,
    ) -> str:
        consulting_prompt = (
            f"You are a Senior Retail Management Consultant. Synthesize the provided database records "
            f"into actionable business insights for executives.\n\n"
            f"CONTEXT SCHEMA ENVIRONMENT:\n{schema_context}\n\n"
            f"RAW BUSINESS METRICS (JSON):\n{db_rows_json}\n\n"
            f"EXECUTIVE INQUIRY: '{user_question}'\n\n"
            f"INSTRUCTIONS:\n"
            f"1. Directly answer the inquiry using exclusively the metrics provided above.\n"
            f"2. Provide 2-3 specific business or inventory strategies (e.g., pricing optimization, restocking advice, capital allocation).\n"
            f"3. Frame responses professionally. Bold key operational performance terms.\n"
            f"4. Never mention database table structures, column definitions, or SQL phrasing to the executive."
        )

        try:
            response = self.client.generate(
                model=model_name,
                prompt=consulting_prompt,
                options={"temperature": 0.2, "num_ctx": 3072, "num_predict": 512},
            )
            return response["response"].strip()
        except Exception as e:
            return f"Strategic analysis compilation failure: {str(e)}"

    def _format_error_payload(self, model: str, sql: str | None, message: str) -> dict:
        """Standardizes edge-case handling across structural barriers."""
        return {
            "success": False,
            "generated_sql": sql,
            "consulting_advice": message,
            "metrics_payload": None,
            "active_model": model,
        }
