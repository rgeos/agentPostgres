import hashlib
import json
import logging
import os
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from agno.agent import Agent
from agno.knowledge.embedder.ollama import OllamaEmbedder
from agno.knowledge.knowledge import Knowledge
from agno.knowledge.reader.pdf_reader import PDFReader
from agno.vectordb.lancedb import LanceDb

from Database import DatabaseTool

logger = logging.getLogger(__name__)


class BaseKnowledgeAgentManager(ABC):
    """Base class providing isolated PDF ingestion, hash tracking, and LanceDB storage."""

    def __init__(
        self,
        pdf_dir: str | Path,
        table_name: str,
        knowledge_name: str,
        knowledge_desc: str,
        db_dir: str | None = None,
    ) -> None:
        self.pdf_dir = Path(pdf_dir)
        self.db_dir = db_dir or os.getenv("LANCE_DB_DATA", "lancedb")
        self.table_name = table_name
        self.manifest_path = Path(self.db_dir) / f"{self.table_name}_manifest.json"

        self.ollama_host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
        self.model_id = os.getenv("OLLAMA_MODEL_ID", "qwen2.5:3b")
        self.embedder_id = os.getenv("OLLAMA_EMBEDDER_ID", "nomic-embed-text")
        self.embedder_dims = int(os.getenv("OLLAMA_EMBEDDER_DIMS", "768"))

        self.db_tool = DatabaseTool()

        if not self.pdf_dir.exists():
            logger.warning(f"📁 Creating missing PDF folder: {self.pdf_dir}")
            self.pdf_dir.mkdir(parents=True, exist_ok=True)

        Path(self.db_dir).mkdir(parents=True, exist_ok=True)

        self.knowledge = Knowledge(
            name=knowledge_name,
            description=knowledge_desc,
            vector_db=LanceDb(
                table_name=self.table_name,
                uri=self.db_dir,
                embedder=OllamaEmbedder(
                    id=self.embedder_id,
                    dimensions=self.embedder_dims,
                    host=self.ollama_host,
                ),
            ),
        )

        self.ingest_pdfs()
        self.agent = self._build_agent()

    @staticmethod
    def _compute_file_hash(file_path: Path) -> str:
        """Computes a SHA-256 checksum to detect content modifications."""
        hasher = hashlib.sha256()
        with file_path.open("rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                hasher.update(chunk)
        return hasher.hexdigest()

    def _load_manifest(self) -> dict[str, str]:
        if self.manifest_path.exists():
            try:
                return json.loads(self.manifest_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError) as e:
                logger.warning(f"⚠️ Could not read manifest {self.manifest_path}: {e}")
        return {}

    def _save_manifest(self, manifest: dict[str, str]) -> None:
        self.manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    def _delete_from_vectordb(self, doc_name: str) -> None:
        """Removes outdated vectors for modified or deleted documents from LanceDB."""
        vector_db = self.knowledge.vector_db
        try:
            if hasattr(vector_db, "delete_by_name"):
                vector_db.delete_by_name(doc_name)
            elif hasattr(vector_db, "table") and vector_db.table is not None:
                safe_name = doc_name.replace("'", "''")
                vector_db.table.delete(f"name = '{safe_name}'")
        except Exception as e:
            logger.warning(f"⚠️ Could not remove old vectors for '{doc_name}': {e}")

    def ingest_pdfs(self) -> dict[str, Any]:
        """Scans assigned folder, detects new/modified/deleted PDFs, and updates LanceDB."""
        manifest = self._load_manifest()
        updated_manifest: dict[str, str] = {}

        pdf_files = list(self.pdf_dir.rglob("*.pdf"))
        current_files = {
            pdf_path.relative_to(self.pdf_dir).as_posix(): pdf_path
            for pdf_path in pdf_files
        }

        added, modified, removed, unchanged = [], [], [], 0

        # 1. Remove vectors for files that were deleted from disk
        for old_name in list(manifest.keys()):
            if old_name not in current_files:
                logger.info(
                    f"🗑️ Removing deleted document from '{self.table_name}': {old_name}"
                )
                self._delete_from_vectordb(old_name)
                removed.append(old_name)

        # 2. Insert new files or re-ingest modified files
        for doc_name, pdf_path in current_files.items():
            file_hash = self._compute_file_hash(pdf_path)
            previous_hash = manifest.get(doc_name)

            if previous_hash == file_hash:
                unchanged += 1
                updated_manifest[doc_name] = file_hash
                continue

            if previous_hash is not None:
                logger.info(
                    f"🔄 Modification detected in '{doc_name}', refreshing vectors..."
                )
                self._delete_from_vectordb(doc_name)
                modified.append(doc_name)
            else:
                logger.info(f"➕ New document detected: '{doc_name}', ingesting...")
                added.append(doc_name)

            self.knowledge.insert(
                name=doc_name,
                path=str(pdf_path),
                reader=PDFReader(split_on_pages=True),
                skip_if_exists=False,  # Manifest already handles deduplication
            )
            updated_manifest[doc_name] = file_hash

        self._save_manifest(updated_manifest)

        summary = {
            "table": self.table_name,
            "directory": str(self.pdf_dir),
            "added": len(added),
            "modified": len(modified),
            "removed": len(removed),
            "unchanged": unchanged,
            "files": {
                "added": added,
                "modified": modified,
                "removed": removed,
            },
        }
        logger.info(
            f"✅ Sync complete for '{self.table_name}': "
            f"+{len(added)} added, ~{len(modified)} modified, -{len(removed)} removed, ={unchanged} unchanged."
        )
        return summary

    @abstractmethod
    def _build_agent(self) -> Agent | None:
        """Subclasses must implement their specific Agno Agent configuration."""
        pass

    def run(self, question: str) -> str:
        if not self.agent:
            raise RuntimeError(
                f"{self.__class__.__name__} failed to initialize due to DB connection error."
            )
        response = self.agent.run(question)
        return response.content
