import os
from agno.agent import Agent
from agno.models.ollama import Ollama
from Database import DatabaseTool

# Define a function to lazily initialize the agent when called
def get_sql_agent():
    db_tool = DatabaseTool()
    return Agent(
        name="AgentSQL",
        model=Ollama(
            id="qwen2.5:3b",
            host=os.getenv("OLLAMA_HOST", "http://localhost:11434")
        ),
        description="You are a data extraction expert that translates natural language inquiries into PostgreSQL statements.",
        instructions=[
            "Always use the run_query tool to inspect structural data or pull records.",
            "You must handle JSONB arrays correctly by employing CROSS JOIN LATERAL sets when needed.",
            "Never run data-modification commands.",
            "Return the resulting dataset or clear answers directly to the user."
        ],
        tools=[db_tool.run_query],
        markdown=True
    )