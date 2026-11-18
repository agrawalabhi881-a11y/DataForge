import hashlib
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class ProvenanceTracker:
    """
    Tracks data lineage, versioning, generation timestamps, and cryptographic hashes
    for ingested datasets to ensure end-to-end reproducibility.
    """

    def __init__(self, metadata_dir: str = "data/metadata"):
        self.metadata_dir = Path(metadata_dir)
        self.metadata_dir.mkdir(parents=True, exist_ok=True)
        self.logger = logging.getLogger(self.__class__.__name__)

    def compute_file_hash(self, file_path: str, chunk_size: int = 8192) -> Optional[str]:
        """Computes SHA-256 hash of a file for integrity verification."""
        path = Path(file_path)
        if not path.exists():
            self.logger.error(f"Cannot compute hash: File not found at {path}")
            return None

        sha256_hash = hashlib.sha256()
        try:
            with open(path, "rb") as f:
                for chunk in iter(lambda: f.read(chunk_size), b""):
                    sha256_hash.update(chunk)
            return sha256_hash.hexdigest()
        except Exception as e:
            self.logger.error(f"Failed to compute hash for {path.name}: {e}")
            return None

    def record_provenance(
        self, 
        dataset_name: str, 
        source_platform: str, 
        file_path: str, 
        additional_metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Generates and saves a JSON provenance ledger entry for an ingested dataset.
        """
        file_hash = self.compute_file_hash(file_path)
        timestamp = datetime.utcnow().isoformat()
        
        provenance_record = {
            "dataset_name": dataset_name,
            "source_platform": source_platform,
            "file_path": str(file_path),
            "sha256_hash": file_hash,
            "ingested_at": timestamp,
            "metadata": additional_metadata or {}
        }

        safe_name = dataset_name.replace("/", "_")
        output_file = self.metadata_dir / f"{safe_name}_provenance.json"
        
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(provenance_record, f, indent=4)

        self.logger.info(f"Provenance record successfully logged at: {output_file}")
        return str(output_file)