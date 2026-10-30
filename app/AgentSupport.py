from agno.agent import Agent
from agno.models.ollama import Ollama
from agno.knowledge.knowledge import Knowledge
from agno.knowledge.embedder.ollama import OllamaEmbedder
from agno.vectordb.pgvector import PgVector
from common import get_db_url, get_ollama_host, get_default_model, get_support_prompt_path, read_prompt_file


class AgentSupport:
    def __init__(self):
        self.knowledge = Knowledge(
            path="/app/documentation",
            vector=PgVector(
                table_name="agent_support_embeddings",
                connection_string=get_db_url(),
                embedder=OllamaEmbedder(id=get_default_model()),
            ),
            num_documents=3,
        )

        try:
            self.knowledge.load(recreate=False)
        except Exception as e:
            exit(f"{e}")

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
