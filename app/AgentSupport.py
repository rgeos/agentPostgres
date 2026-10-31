from agno.agent import Agent
from agno.models.ollama import Ollama
from agno.knowledge.knowledge import Knowledge
from agno.knowledge.embedder.ollama import OllamaEmbedder
from agno.vectordb.pgvector import PgVector

from app.main import logger
from common import get_db_url, get_ollama_host, get_default_model, get_support_prompt_path, read_prompt_file


class AgentSupport:
    def __init__(self):
        self.knowledge = Knowledge(
            vector=PgVector(
                table_name="agent_support_embeddings",
                db_url=get_db_url(),
                embedder=OllamaEmbedder(id=get_default_model(), host=get_ollama_host()),
            ),
        )

        try:
            self.knowledge.insert(path="app/documentation")
        except Exception as e:
            logger.error(e)

        self.agent = Agent(
            name="Agent - Support",
            model=Ollama(id=get_default_model(), host=get_ollama_host()),
            knowledge=self.knowledge,
            search_knowledge=True,
            markdown=True,
            instructions=read_prompt_file(get_support_prompt_path()),
            telemetry=False,
        )

    def run(self, message: str) -> str:
        response = self.agent.run(message)
        return response.content
