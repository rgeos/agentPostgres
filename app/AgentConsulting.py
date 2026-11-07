import logging
import os
from pathlib import Path

from agno.agent import Agent
from agno.models.ollama import Ollama

from BaseKnowledgeAgent import BaseKnowledgeAgentManager

logger = logging.getLogger(__name__)


class ConsultingAgentManager(BaseKnowledgeAgentManager):
    def __init__(
        self,
        pdf_dir: str | Path | None = None,
        db_dir: str | None = None,
    ) -> None:
        resolved_pdf_dir = pdf_dir or os.getenv(
            "CONSULTING_PDF_DIRECTORY", "documentation/consulting"
        )
        super().__init__(
            pdf_dir=resolved_pdf_dir,
            table_name="consulting_knowledge_base",
            knowledge_name="AgentConsulting Knowledge Base",
            knowledge_desc="Read from local Consulting PDF reports and strategies",
            db_dir=db_dir,
        )

    def _build_agent(self) -> Agent | None:
        connection_status = self.db_tool.verify_connection()
        if not connection_status["status"]:
            logger.error(f"❌ Cannot proceed: {connection_status['message']}")
            return None

        return Agent(
            name="AgentConsulting",
            model=Ollama(
                id=self.model_id,
                host=self.ollama_host,
            ),
            description="You are a senior enterprise management consultant with access to live SQL databases and strategic PDF reports.",
            instructions=[
                "Synthesize high-level corporate strategies and supply-chain metrics based on live operational numbers and local strategic PDF documents.",
                "Query the database via tools to check current inventory, stock levels, and historical order data before producing advice.",
                "Search the knowledge base for corporate guidelines, benchmarks, and strategic frameworks.",
                "Provide strategic, actionable advice to help management balance production profiles and reduce product stocks safely.",
            ],
            tools=[self.db_tool.run_query],
            knowledge=self.knowledge,
            search_knowledge=True,
            markdown=True,
        )
