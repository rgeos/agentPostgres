import os
import glob
import json
import ollama
from pypdf import PdfReader
from Database import DatabaseTool, DecimalEncoder
from AgentSQL import AgentSQL


class AgentSupport:
    def __init__(
        self, target_table: str = "products", pdf_dir_path: str = "/documentation"
    ):
        ollama_host = os.getenv("OLLAMA_HOST", "http://ollama:11434")
        self.client = ollama.Client(host=ollama_host)
        self.default_model = os.getenv("OLLAMA_MODEL", "qwen2.5:3b")
        self.target_schema = os.getenv("TARGET_SCHEMA", "public_read_only")
        self.prompt_filepath = os.getenv(
            "SUPPORT_PROMPT_PATH", "prompts/agent_support.txt"
        )

        # Strict Boundary Declarations
        self.target_table = target_table
        self.pdf_dir_path = pdf_dir_path
        self.db_tool = DatabaseTool()

        if not os.path.exists(self.pdf_dir_path):
            os.makedirs(self.pdf_dir_path)

    def _load_prompt_template(self) -> str:
        try:
            with open(self.prompt_filepath, "r", encoding="utf-8") as f:
                return f.read()
        except Exception:
            return "Help customer.\nTABLES:\n{table_data_json}\nMANUALS:\n{pdf_documentation_text}\nINQUIRY:\n{customer_question}"

    def _extract_text_from_pdfs(self) -> str:
        combined_pdf_text = []
        pdf_pattern = os.path.join(self.pdf_dir_path, "*.pdf")
        pdf_files = glob.glob(pdf_pattern)

        for file_path in pdf_files:
            try:
                reader = PdfReader(file_path)
                for page in reader.pages:
                    text = page.extract_text()
                    if text:
                        combined_pdf_text.append(text)
            except Exception as e:
                print(
                    f"[AgentSupport] Warning: Skipping unreadable file {file_path}. Error: {e}"
                )

        return "\n".join(combined_pdf_text)

    def _query_dedicated_table(self, user_question: str) -> str:
        clean_keyword = "".join(
            ch for ch in user_question if ch.isalnum() or ch.isspace()
        ).strip()
        first_word = clean_keyword.split()[0] if clean_keyword else ""

        # Enforced structural lock: Queries can only target schema.table. Probably we won't need LIMIT?!?!?
        sql_query = f"""
            SELECT * FROM {self.target_schema}.{self.target_table}
            WHERE name ILIKE '%{first_word}%' 
               OR description ILIKE '%{first_word}%'
            LIMIT 5;
        """
        try:
            db_rows = self.db_tool.execute_read_query_raw(sql_query)
            return json.dumps(db_rows, cls=DecimalEncoder)
        except Exception:
            return "[]"

    # make the agent collaborate
    def run_collaboration(
        self,
        customer_question: str,
        agent_sql_instance: AgentSQL,
        selected_model: str | None = None,
    ) -> dict:
        active_model = selected_model if selected_model else self.default_model

        print("[COLLABORATION] Upgrading AgentSupport query parsing via AgentSQL")
        generated_sql = agent_sql_instance.sql_generation_worker.generate_query(
            customer_question, model_name=active_model
        )

        table_data_json = "[]"
        if generated_sql and generated_sql.strip().lower().startswith("select"):
            try:
                db_rows = self.db_tool.execute_read_query_raw(generated_sql)
                table_data_json = json.dumps(db_rows, cls=DecimalEncoder)
            except Exception:
                table_data_json = self._query_dedicated_table(customer_question)
        else:
            table_data_json = self._query_dedicated_table(customer_question)

        pdf_documentation_text = (
            self._extract_text_from_pdfs() or "[No PDF manuals found]"
        )

        template = self._load_prompt_template()
        system_prompt = template.format(
            table_data_json=table_data_json,
            pdf_documentation_text=pdf_documentation_text,
            customer_question=customer_question,
        )

        try:
            response = self.client.generate(
                model=active_model,
                prompt=system_prompt,
                options={"temperature": 0.1, "num_ctx": 4096},
            )
            reply = response["response"].strip()
        except Exception:
            reply = "Internal processing link error."

        return {
            "agent_name": "AgentSupport+AgentSQL_Collaborative",
            "customer_reply": reply,
            "generated_sql_used": generated_sql,
        }

    def _generate_advice(
        self, customer_question: str, selected_model: str | None = None
    ) -> dict:
        active_model = selected_model if selected_model else self.default_model

        table_data_json = self._query_dedicated_table(customer_question)
        pdf_documentation_text = (
            self._extract_text_from_pdfs() or "[No PDF manuals found in directory]"
        )

        template = self._load_prompt_template()
        system_prompt = template.format(
            table_data_json=table_data_json,
            pdf_documentation_text=pdf_documentation_text,
            customer_question=customer_question,
        )

        try:
            response = self.client.generate(
                model=active_model,
                prompt=system_prompt,
                options={"temperature": 0.1, "num_ctx": 4096},
            )
            reply = response["response"].strip()
        except Exception:
            reply = "I am sorry, I am currently unable to process this request due to an internal system link error."

        return {
            "agent_name": "AgentSupport",
            "customer_reply": reply,
            "sources_checked": {
                "database_table": f"{self.target_schema}.{self.target_table}",
                "pdf_folder": self.pdf_dir_path,
            },
        }
