import os
import json
import ollama
from Database import DatabaseTool, SchemaDiscoverer, DecimalEncoder
from AgentSQL import SQLGenerationAgent
from PromptWatchdog import watchdog


class AgentConsulting:
    def __init__(self):
        ollama_host = os.getenv("OLLAMA_HOST", "http://ollama:11434")
        self.client = ollama.Client(host=ollama_host)
        self.default_model = os.getenv("OLLAMA_MODEL", "qwen2.5:3b")
        self.target_schema = os.getenv("TARGET_SCHEMA", "public_read_only")
        self.prompt_filepath = os.getenv(
            "CONSULTING_PROMPT_PATH", "prompts/agent_consulting.txt"
        )

        fallback = "You are a consultant.\nCONTEXT:\n{schema_context}\nDATA:\n{db_rows_json}\nINQUIRY:\n{user_question}"
        watchdog.register_prompt(
            file_path=self.prompt_filepath,
            required_keys=["schema_context", "db_rows_json", "user_question"],
            fallback_text=fallback,
        )

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

        consulting_advice = self._generate_advice(
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

    # make the agent collaborate
    def run_collaboration(
        self, user_question: str, agent_sql_instance, selected_model: str | None = None
    ) -> dict:
        """
        Collaboration: AgentSQL fetches and cleans data,
        AgentConsulting synthesizes corporate strategy from it.
        """
        active_model = selected_model if selected_model else self.default_model

        # 1. Delegate data gathering to AgentSQL
        print("[COLLABORATION] Routing data gathering to AgentSQL")
        sql_result = agent_sql_instance.run_workflow(
            user_question, selected_model=active_model
        )

        # If AgentSQL failed to get data, return its fallback message safely
        if not sql_result.get("tool_called") or not sql_result.get("raw_db_rows"):
            return {
                "success": False,
                "consulting_advice": f"Consulting blocked. AgentSQL Reason: {sql_result['answer']}",
                "active_model": active_model,
            }

        # 2. Extract clean data payloads from AgentSQL's output
        db_rows = sql_result["raw_db_rows"]
        clean_json_data = json.dumps(db_rows, cls=DecimalEncoder)
        live_schema_context = self.discoverer.get_active_schema_documentation()

        # 3. AgentConsulting performs strategic synthesis
        print("[COLLABORATION] Routing data to AgentConsulting for strategic advice")
        strategic_advice = self._generate_advice(
            user_question=user_question,
            db_rows_json=clean_json_data,
            schema_context=live_schema_context,
            model_name=active_model,
        )

        return {
            "success": True,
            "generated_sql": sql_result["generated_sql"],
            "metrics_payload": db_rows,
            "consulting_advice": strategic_advice,
            "active_model": active_model,
        }

    def _generate_advice(
        self,
        user_question: str,
        db_rows_json: str,
        schema_context: str,
        model_name: str,
    ) -> str:
        # Instant memory load from pre-cached layout data
        template = watchdog.get_prompt(self.prompt_filepath)
        consulting_prompt = template.format(
            schema_context=schema_context,
            db_rows_json=db_rows_json,
            user_question=user_question,
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

    @staticmethod
    def _format_error_payload(model: str, sql: str | None, message: str) -> dict:
        """Standardizes edge-case handling across structural barriers."""
        return {
            "success": False,
            "generated_sql": sql,
            "consulting_advice": message,
            "metrics_payload": None,
            "active_model": model,
        }
