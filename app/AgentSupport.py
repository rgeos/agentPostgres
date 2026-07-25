import os
import glob
import json
import ollama
from pypdf import PdfReader
from database import DatabaseTool, DecimalEncoder


class AgentSupport:
    """
    Customer Support Specialist: Explicitly restricted to a single database table
    and a local directory of product manual PDFs.
    """

    def __init__(
        self, target_table: str = "products", pdf_dir_path: str = "./support_pdfs"
    ):
        ollama_host = os.getenv("OLLAMA_HOST", "http://ollama:11434")
        self.client = ollama.Client(host=ollama_host)
        self.default_model = os.getenv("OLLAMA_MODEL", "qwen2.5:3b-instruct-q4_K_M")
        self.target_schema = os.getenv("TARGET_SCHEMA", "public_read_only")

        # Strict Boundary Declarations
        self.target_table = target_table
        self.pdf_dir_path = pdf_dir_path
        self.db_tool = DatabaseTool()

        # Automatically generate target folder structure if missing
        if not os.path.exists(self.pdf_dir_path):
            os.makedirs(self.pdf_dir_path)

    def _extract_text_from_pdfs(self) -> str:
        """Searches and parses text content solely from the locked PDF folder."""
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
        """Executes a basic keyword search restricted solely to the designated table."""
        # Clean question tokens to prevent query injection risks
        clean_keyword = "".join(
            ch for ch in user_question if ch.isalnum() or ch.isspace()
        ).strip()
        first_word = clean_keyword.split()[0] if clean_keyword else ""

        # Enforced structural lock: Queries can only target schema.table
        sql_query = f"""
            SELECT * FROM {self.target_schema}.{self.target_table}
            WHERE name ILIKE '%{first_word}%' 
               OR description ILIKE '%{first_word}%'
            LIMIT 5;
        """

        try:
            db_rows = self.db_tool.execute_read_query_raw(sql_query)
            return json.dumps(db_rows, cls=DecimalEncoder)
        except Exception as e:
            return f"[]"

    def handle_customer_inquiry(
        self, customer_question: str, selected_model: str | None = None
    ) -> dict:
        """Orchestrates sandboxed data sources to answer customer product questions."""
        active_model = selected_model if selected_model else self.default_model

        # Step 1: Gather data strictly from isolated silos
        table_data_json = self._query_dedicated_table(customer_question)
        pdf_documentation_text = self._extract_text_from_pdfs()

        # Step 2: Build strict guardrail instructions
        system_prompt = (
            f"You are 'AgentSupport', an expert customer service assistant. You help customers with product questions.\n"
            f"CRITICAL SAFETY RULE: You are strictly forbidden from using external knowledge, guessing, or searching outside your provided data sources.\n"
            f"If the answer cannot be found in the data below, state politely that you do not have that product information available.\n\n"
            f"--- DATA SOURCE 1: LIVE INVENTORY TABLE ({self.target_schema}.{self.target_table}) ---\n"
            f"{table_data_json}\n\n"
            f"--- DATA SOURCE 2: LOCAL PRODUCT MANUALS (PDF TEXT) ---\n"
            f"{pdf_documentation_text or '[No PDF manuals found in directory]'}\n\n"
            f"CUSTOMER INQUIRY: '{customer_question}'\n"
            f"ANSWER:"
        )

        try:
            response = self.client.generate(
                model=active_model,
                prompt=system_prompt,
                options={"temperature": 0.1, "num_ctx": 4096},
            )
            reply = response["response"].strip()
        except Exception as e:
            reply = f"I am sorry, I am currently unable to process this request due to an internal system link error."

        return {
            "agent_name": "AgentSupport",
            "customer_reply": reply,
            "sources_checked": {
                "database_table": f"{self.target_schema}.{self.target_table}",
                "pdf_folder": self.pdf_dir_path,
            },
        }
