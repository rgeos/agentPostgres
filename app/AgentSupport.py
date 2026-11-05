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
            description="You are a client-facing product support specialist.",
            instructions=[
                "Answer customer lookups regarding product lineage, origins, and operational manual workflows.",
                "Exclusively use local documentation tools to fetch context information offline.",
                "Be factual, precise, and never invent detail parameters not present in local manuals.",
            ],
            tools=[self.lookup_pdf_manuals],
            markdown=True,
        )

    def run(self, question: str) -> str:
        response = self.agent.run(question)
        return response.content
