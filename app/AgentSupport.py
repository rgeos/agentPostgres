import logging
import os
from pathlib import Path

from agno.agent import Agent
from agno.models.ollama import Ollama

from BaseKnowledgeAgent import BaseKnowledgeAgentManager

logger = logging.getLogger(__name__)


class SupportAgentManager(BaseKnowledgeAgentManager):
    def __init__(
        self,
        pdf_dir: str | Path | None = None,
        db_dir: str | None = None,
    ) -> None:
        resolved_pdf_dir = pdf_dir or os.getenv(
            "SUPPORT_PDF_DIRECTORY", "documentation/support"
        )
        super().__init__(
            pdf_dir=resolved_pdf_dir,
            table_name="support_knowledge_base",
            knowledge_name="AgentSupport Knowledge Base",
            knowledge_desc="Read from local Support PDF documentation",
            db_dir=db_dir,
        )

    def _build_agent(self) -> Agent | None:
        """
        This agent needs only PDF folder access.
        No access to PostgreSQL required
        """
        return Agent(
            name="AgentSupport",
            model=Ollama(
                id=self.model_id,
                host=self.ollama_host,
                options={"temperature": 0.0},
            ),
            description="You are a strict, closed-domain SupportAgent. You have access to a PDF document retriever and a Database query tool.",
            instructions=[
                "EXCLUSIVELY use local documentation tools to fetch context information offline.",
                "Answer questions EXCLUSIVELY using the facts explicitly provided in the retrieved PDF context or the SQL database results.",
                "Do NOT use any pre-trained general knowledge, external information, or generic assumptions to answer or complete gaps.",
                'If the combined data from the PDF folder and the Database does not contain the answer, you must respond exactly with: "I\'m sorry, but I cannot find that information in the provided documents or database."',
                "Never make up facts, URLs, or instructions. If it is not in the data, it does not exist.",
                "Be factual, precise, and never invent detail parameters not present in local manuals.",
            ],
            tools=[self.db_tool.run_query],
            knowledge=self.knowledge,
            search_knowledge=True,
            markdown=True,
            debug_mode=True,
        )
