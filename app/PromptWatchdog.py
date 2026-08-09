import os
import time
import threading
import logging
from string import Formatter

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] (%(threadName)s) %(message)s",
)
logger = logging.getLogger("PromptWatchdog")


class PromptWatchdog:
    """
    Thread-safe, non-blocking prompt engine. Pre-caches content on initialization
    and runs a background file monitor to hot-reload updates seamlessly.
    """

    def __init__(self, check_interval_seconds: float = 1.0):
        self.check_interval = check_interval_seconds
        self._cache = {}  # Holds active, validated prompt string data
        self._file_states = {}  # Tracks last modification timestamps (mtime)
        self._fallbacks = {}  # Hardcoded structural backups
        self._required_keys = {}  # Set of mandatory placeholder keys for validation
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._monitor_thread = None

    def register_prompt(
        self, file_path: str, required_keys: list[str], fallback_text: str
    ):
        """Registers a target prompt file configuration and pre-caches its initial values."""
        normalized_path = os.path.normpath(file_path)
        self._required_keys[normalized_path] = set(required_keys)
        self._fallbacks[normalized_path] = fallback_text

        # Initial baseline load (Pre-Caching)
        success = self._reload_file(normalized_path)
        if not success:
            logger.warning(
                f"Initial load failed for '{normalized_path}'. Armed fallback string structure."
            )
            with self._lock:
                self._cache[normalized_path] = fallback_text

    def get_prompt(self, file_path: str) -> str:
        """Thread-safe retrieval of the active pre-cached prompt template string."""
        normalized_path = os.path.normpath(file_path)
        with self._lock:
            return self._cache.get(
                normalized_path, self._fallbacks.get(normalized_path, "")
            )

    def start(self):
        """Launches the background file watchdog processor loop thread."""
        if self._monitor_thread and self._monitor_thread.is_alive():
            return
        self._stop_event.clear()
        self._monitor_thread = threading.Thread(
            target=self._watch_loop, name="PromptWatchdogWorker", daemon=True
        )
        self._monitor_thread.start()
        logger.info("Asynchronous prompt compilation watchdog worker initialized.")

    def stop(self):
        """Gracefully signs off background file monitors."""
        self._stop_event.set()
        if self._monitor_thread:
            self._monitor_thread.join()
            logger.info("Prompt watchdog engine halted safely.")

    def _validate_placeholders(self, file_path: str, content: str) -> bool:
        """Parses structural text layout arrays to protect against formatting crashes."""
        try:
            # Parse text safely through standard string extraction logic
            parsed_blocks = Formatter().parse(content)
            extracted_keys = {
                field_name
                for _, field_name, _, _ in parsed_blocks
                if field_name is not None
            }
        except ValueError as exc:
            logger.error(
                f"CRITICAL COMPILATION FAULT: File '{file_path}' has broken brace alignment matching layouts! "
                f"Details: {exc}. Update operation rejected."
            )
            return False

        required = self._required_keys.get(file_path, set())
        missing_keys = required - extracted_keys

        if missing_keys:
            logger.error(
                f"VALIDATION ERROR: Configuration file '{file_path}' rejected! "
                f"Missing critical structural placeholder keys: {list(missing_keys)}. "
                f"Required context relies on: {list(required)}."
            )
            return False

        return True

    def _reload_file(self, file_path: str) -> bool:
        """Reads, validates, and commits text mutations to the hot memory arrays."""
        if not os.path.exists(file_path):
            return False

        try:
            current_mtime = os.stat(file_path).st_mtime
            with open(file_path, "r", encoding="utf-8") as f:
                raw_content = f.read()

            # Execute integrity runtime screen
            if not self._validate_placeholders(file_path, raw_content):
                # Update file state time marker regardless to prevent logging loops on bad code
                self._file_states[file_path] = current_mtime
                return False

            with self._lock:
                self._cache[file_path] = raw_content
                self._file_states[file_path] = current_mtime

            logger.info(
                f"Dynamic caching hot-reload successful for template footprint: '{file_path}'"
            )
            return True

        except Exception as e:
            logger.error(
                f"Unchecked file system stream barrier hit for '{file_path}': {e}"
            )
            return False

    def _watch_loop(self):
        """Continually evaluates active OS storage footprints using memory-light indexing."""
        while not self._stop_event.is_set():
            # Create a shallow snapshot of active targets to keep lock times minimal
            with self._lock:
                tracked_files = list(self._required_keys.keys())

            for file_path in tracked_files:
                if not os.path.exists(file_path):
                    continue

                try:
                    current_mtime = os.stat(file_path).st_mtime
                    last_known_mtime = self._file_states.get(file_path, 0.0)

                    if current_mtime > last_known_mtime:
                        logger.info(
                            f"Mutation footprint detected on tracking target: '{file_path}'"
                        )
                        self._reload_file(file_path)
                except Exception as e:
                    logger.debug(f"Failed to stat file {file_path}: {e}")

            time.sleep(self.check_interval)


# Instantiate a single shared instance for use across all application module borders
watchdog = PromptWatchdog(check_interval_seconds=1.0)
