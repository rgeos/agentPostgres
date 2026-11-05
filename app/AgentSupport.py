import logging
import os
from agno.agent import Agent
from agno.models.ollama import Ollama
from pypdf import PdfReader
from Database import DatabaseTool

# todo - remove this
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SupportAgentManager:
    def __init__(self):
        self.doc_dir = "./app/documentation"
        self.db_tool = DatabaseTool()
        self.agent = self._build_agent()

    def lookup_pdf_manuals(self, search_keyword: str) -> str:
        """
        Searches local PDF manuals for pages containing the search keyword.

        PDF extensions are matched without regard to case. Files are searched
        directly inside the documentation folder, not in subfolders.
        :param search_keyword: Word or topic to search within local manuals.
        """
        if not os.path.exists(self.doc_dir):
            logger.error(f"Directory {self.doc_dir} does not exist")
            return "No manual documentation folder configured locally."

        try:
            files = os.listdir(self.doc_dir)
        except OSError:
            logger.exception(f"Could not list files from {self.doc_dir} directory")
            return "Unable to read the local documentation folder."

        logger.info("Files found in %s: %s", self.doc_dir, files or "none")

        extracted_text = ""
        for file in os.listdir(self.doc_dir):
            if file.endswith(".pdf"):
                try:
                    reader = PdfReader(os.path.join(self.doc_dir, file))
                    for page in reader.pages:
                        text = page.extract_text()
                        if search_keyword.lower() in text.lower():
                            extracted_text += f"\n--- From {file} ---\n" + text[:1500]
                except Exception as e:
                    continue
        return (
            extracted_text
            if extracted_text
            else "No relevant information found in local PDF manuals."
        )

    def get_database_schema(self) -> str:
        return self.db_tool.run_query(
            """
            SELECT table_schema, table_name, column_name, data_type
            FROM information_schema.columns
            WHERE table_schema NOT IN ('pg_catalog', 'information_schema')
            ORDER BY table_schema, table_name, ordinal_position
            """
        )

    def run_database_query(self, query: str) -> str:
        return self.db_tool.run_query(query)

    def _build_agent(self) -> Agent:
        connection_status = self.db_tool.verify_connection()

        if not connection_status["status"]:
            print(f"Cannot proceed: {connection_status['message']}")
            return None
        return Agent(
            name="AgentSupport",
            model=Ollama(
                id="qwen2.5:3b", host=os.getenv("OLLAMA_HOST", "http://localhost:11434")
            ),
            description="You are a strict, closed-domain SupportAgent. You have access to two tools: a PDF document retriever and a Database query tool.",
            instructions=[
                "EXCLUSIVELY use local documentation tools to fetch context information offline.",
                "Answer questions EXCLUSIVELY using the facts explicitly provided in the retrieved PDF context or the SQL database results.",
                "Do NOT use any pre-trained general knowledge, external information, or generic assumptions to answer or complete gaps.",
                "If the combined data from the PDF folder and the Database does not contain the answer, you must respond exactly with: \"I'm sorry, but I cannot find that information in the provided documents or database.",
                "Never make up facts, URLs, or instructions. If it is not in the data, it does not exist.",
                "Be factual, precise, and never invent detail parameters not present in local manuals.",
            ],
            tools=[
                self.lookup_pdf_manuals,
                self.get_database_schema,
                self.run_database_query,
            ],
            markdown=True,
        )

    def run(self, question: str) -> str:
        response = self.agent.run(question)
        return response.content
