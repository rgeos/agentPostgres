import logging
import os
from pathlib import Path

from agno.agent import Agent
from agno.models.ollama import Ollama
from agno.knowledge.embedder.ollama import OllamaEmbedder
from agno.knowledge.knowledge import Knowledge
from agno.knowledge.reader.pdf_reader import PDFReader
from agno.vectordb.lancedb import LanceDb

from Database import DatabaseTool

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SupportAgentManager:
    def __init__(
        self,
        pdf_dir: str | Path = os.getenv("PDF_DIRECTORY", "documentation"),
        db_dir: str | str = os.getenv("LANCE_DB_DATA", "lancedb"),
    ) -> None:
        self.pdf_dir = Path(pdf_dir)
        self.db_dir = db_dir

        self.db_tool = DatabaseTool()
        self.ollama_host = os.getenv("OLLAMA_HOST", "http://localhost:11434")

        if not self.pdf_dir.exists():
            logger.error(f"❌ PDF folder does not exist: {self.pdf_dir}")
            raise FileNotFoundError(f"PDF folder does not exist: {self.pdf_dir}")

        self.knowledge = Knowledge(
            name="AgentSupport Knowledge Base",
            description="Read from local PDF files",
            vector_db=LanceDb(
                table_name="pdf_knowledge_base",
                uri=self.db_dir,
                embedder=OllamaEmbedder(
                    id="nomic-embed-text",  # todo - pick it up from the .env
                    dimensions=768,
                    host=self.ollama_host,
                ),
            ),
        )

        self._ingest_pdfs()

        self.agent = self._build_agent()

    def _ingest_pdfs(self) -> None:
        pdf_files = list(self.pdf_dir.glob("*.pdf"))

        if not pdf_files:
            logger.warning("⚠ No PDF files found in this directory")
            raise NotADirectoryError(
                f"⚠ No PDF documents found inside '{self.pdf_dir}'. Add files to your local folder."
            )

        logger.info(f"ℹ️ Found {len(pdf_files)} PDF file(s) to ingest...")
        for pdf_path in pdf_files:
            self.knowledge.insert(
                name=pdf_path.relative_to(self.pdf_dir).as_posix(),
                path=str(pdf_path),
                reader=PDFReader(split_on_pages=True),
                skip_if_exists=True,
            )
        logger.info(f"✅ Ingestion complete.")

    def _build_agent(self) -> Agent:
        connection_status = self.db_tool.verify_connection()

        if not connection_status["status"]:
            logger.error(f"❌ Cannot proceed: {connection_status['message']}")
            return None
        return Agent(
            name="AgentSupport",
            model=Ollama(
                id="qwen2.5:3b",  # todo - pick it up from the .env
                host=self.ollama_host,
                options={"temperature": 0.0},
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
            knowledge=self.knowledge,
            search_knowledge=True,
            markdown=True,
            debug_mode=True,
        )

    def run(self, question: str) -> str:
        response = self.agent.run(question)
        return response.content
