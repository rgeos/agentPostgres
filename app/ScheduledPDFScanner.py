import logging
import schedule

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ScheduledPDFScanner:
    """Scans and updates the knowledge base at a specific time every day."""

    def __init__(self, manager_instance):
        self.manager = manager_instance

    def scan_and_ingest(self):
        """The cron-like job triggered by the scheduler."""
        logger.info("🕒 Daily scheduled scan started...")
        try:
            pdf_files = list(self.manager.pdf_dir.glob("*.pdf"))
            if not pdf_files:
                logger.info("ℹ️ No PDF files found during this scan.")
                return

            new_files_count = 0

            for pdf_path in pdf_files:
                file_name = pdf_path.relative_to(self.manager.pdf_dir).as_posix()

                # skip_if_exists=True ensures only *newly added* files get processed
                logger.info(f"ℹ️ Checking tracking state for: {file_name}")
                self.manager.knowledge.insert(
                    name=file_name,
                    path=str(pdf_path),
                    reader=None,  # Falls back to the class's default configuration
                    skip_if_exists=True,
                )
                new_files_count += 1

            if new_files_count > 0:
                logger.info(
                    f"✅ Daily synchronization complete. Processed {new_files_count} files."
                )
            else:
                logger.info("✅ Daily synchronization complete. No new updates found.")

        except Exception as e:
            logger.error(f"❌ Error occurred during scheduled scan: {str(e)}")
