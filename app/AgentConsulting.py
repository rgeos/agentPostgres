import os
from agno.agent import Agent
from agno.models.ollama import Ollama
from Database import DatabaseTool


class ConsultingAgentManager:
    def __init__(self):
        self.db_tool = DatabaseTool()
        self.agent = self._build_agent()

    def _build_agent(self) -> Agent:
        connection_status = self.db_tool.verify_connection()

        if not connection_status["status"]:
            print(f"Cannot proceed: {connection_status['message']}")
            return None
        return Agent(
            name="AgentConsulting",
            model=Ollama(
                id="qwen2.5:3b", host=os.getenv("OLLAMA_HOST", "http://localhost:11434")
            ),
            description="You are a senior enterprise management consultant.",
            instructions=[
                "Synthesize high-level corporate strategies and supply-chain metrics based on live operational numbers.",
                "Query the database via tools to check current inventory, stock levels, and historical order data before producing advice.",
                "Provide strategic, actionable advice to help management balance production profiles and reduce product stocks safely.",
            ],
            tools=[self.db_tool.run_query],
            markdown=True,
        )

    def run(self, question: str) -> str:
        response = self.agent.run(question)
        return response.content
