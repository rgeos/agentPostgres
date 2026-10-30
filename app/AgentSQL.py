from agno.agent import Agent
from agno.models.ollama import Ollama
from agno.tools.sql import SQLTools
from common import get_db_url, get_ollama_host, get_default_model, get_sql_prompt_path, read_prompt_file


class AgentSQL:
    def __init__(self):
        sql_tools = SQLTools(
            connection_string=get_db_url(),
            cls_kwargs={"echo": False},
        )

        self.agent = Agent(
            name="Agent - SQL",
            model=Ollama(id=get_default_model(), host=get_ollama_host()),
            tools=[sql_tools],
            markdown=True,
            instructions=read_prompt_file(get_sql_prompt_path()),
            show_tool_calls=True,
            telemetry=False,
        )

    def run(self, message: str) -> str:
        response = self.agent.run(message)
        return response.content
