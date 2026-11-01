import os
from agno.agent import Agent
from agno.models.ollama import Ollama
from Database import DatabaseTool


class SQLAgentManager:
    def __init__(self):
        self.db_tool = DatabaseTool()
        self.agent = self._build_agent()

    def _build_agent(self) -> Agent:
        connection_status = self.db_tool.verify_connection()

        if not connection_status["status"]:
            print(f"Cannot proceed: {connection_status['message']}")
            return None
        return Agent(
            name="AgentSQL",
            model=Ollama(
                id="qwen2.5:3b", host=os.getenv("OLLAMA_HOST", "http://localhost:11434")
            ),
            description="You are a data extraction expert that translates natural language inquiries into PostgreSQL statements.",
            instructions=[
                "Always use the run_query tool to inspect structural data or pull records.",
                "You must handle JSONB arrays correctly by employing CROSS JOIN LATERAL sets when needed.",
                "Never run data-modification commands.",
                "Return the resulting dataset or clear answers directly to the user.",
            ],
            tools=[self.db_tool.run_query],
            markdown=True,
        )

    def run(self, question: str) -> str:
        response = self.agent.run(question)
        return response.content
