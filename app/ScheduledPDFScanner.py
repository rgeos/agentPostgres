import logging
from typing import Any
from BaseKnowledgeAgent import BaseKnowledgeAgentManager

logger = logging.getLogger(__name__)


class ScheduledPDFScanner:
    """Scans and updates a manager's knowledge base on a schedule or manual trigger."""

    def __init__(self, manager_instance: BaseKnowledgeAgentManager) -> None:
        self.manager = manager_instance

    def scan_and_ingest(self) -> dict[str, Any]:
        """Runs the PDF synchronization and returns a summary report."""
        logger.info(
            f"🕒 Sync started for '{self.manager.table_name}' "
            f"in '{self.manager.pdf_dir}'..."
        )
        try:
            summary = self.manager.ingest_pdfs()
            return {"status": "success", **summary}
        except Exception as e:
            logger.error(
                f"❌ Error during sync for '{self.manager.table_name}': {str(e)}"
            )
            raise
