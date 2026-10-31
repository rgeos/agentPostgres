import os
from agno.agent import Agent
from agno.models.ollama import Ollama
from Database import DatabaseTool

def get_consulting_agent():
    db_tool = DatabaseTool()
    return Agent(
        name="AgentConsulting",
        model=Ollama(
            id="qwen2.5:3b",
            host=os.getenv("OLLAMA_HOST", "http://localhost:11434")
        ),
        description="You are a senior enterprise management consultant.",
        instructions=[
            "Synthesize high-level corporate strategies and supply-chain metrics based on live operational numbers.",
            "Query the database via tools to check current inventory, stock levels, and historical order data before producing advice.",
            "Provide strategic, actionable advice to help management balance production profiles and reduce product stocks safely."
        ],
        tools=[db_tool.run_query],
        markdown=True
    )