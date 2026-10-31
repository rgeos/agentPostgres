import os
from agno.agent import Agent
from agno.models.ollama import Ollama
from pypdf import PdfReader


def lookup_pdf_manuals(search_keyword: str) -> str:
    """
    Searches through local infrastructure document manuals and PDF guides for specific support matching lines.

    :param search_keyword: Word or topic to search within local manuals.
    """
    doc_dir = "./app/documentation"
    if not os.path.exists(doc_dir):
        return "No manual documentation folder configured locally."

    extracted_text = ""
    for file in os.listdir(doc_dir):
        if file.endswith(".pdf"):
            try:
                reader = PdfReader(os.path.join(doc_dir, file))
                for page in reader.pages:
                    text = page.extract_text()
                    if search_keyword.lower() in text.lower():
                        extracted_text += f"\n--- From {file} ---\n" + text[:1500]
            except Exception as e:
                continue
    return extracted_text if extracted_text else "No relevant information found in local PDF manuals."


def get_support_agent():
    return Agent(
        name="AgentSupport",
        model=Ollama(
            id="qwen2.5:3b",
            host=os.getenv("OLLAMA_HOST", "http://localhost:11434")
        ),
        description="You are a client-facing product support specialist.",
        instructions=[
            "Answer customer lookups regarding product lineage, origins, and operational manual workflows.",
            "Exclusively use local documentation tools to fetch context information offline.",
            "Be factual, precise, and never invent detail parameters not present in local manuals."
        ],
        tools=[lookup_pdf_manuals],
        markdown=True
    )