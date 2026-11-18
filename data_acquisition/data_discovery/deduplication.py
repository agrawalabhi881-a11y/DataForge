import logging
from typing import List, Dict, Any
from difflib import SequenceMatcher

logger = logging.getLogger(__name__)

class DatasetDeduplicator:
    """
    Identifies and removes duplicate or highly overlapping dataset entries
    discovered across multiple external repositories.
    """

    def __init__(self, similarity_threshold: float = 0.85):
        self.similarity_threshold = similarity_threshold
        self.logger = logging.getLogger(self.__class__.__name__)

    def _calculate_similarity(self, name_a: str, name_b: str) -> float:
        """Calculates string similarity ratio between two dataset titles/references."""
        return SequenceMatcher(None, name_a.lower(), name_b.lower()).ratio()

    def deduplicate_sources(self, candidate_datasets: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Filters a list of candidate dataset dictionaries, removing duplicates
        based on name similarity and source priority.
        """
        self.logger.info(f"Running deduplication across {len(candidate_datasets)} candidate datasets...")
        unique_datasets = []

        for candidate in candidate_datasets:
            is_duplicate = False
            candidate_name = candidate.get("name", "")

            for unique in unique_datasets:
                similarity = self._calculate_similarity(candidate_name, unique.get("name", ""))
                if similarity >= self.similarity_threshold:
                    self.logger.info(f"Duplicate detected: '{candidate_name}' matches existing '{unique.get('name')}' (Similarity: {similarity:.2f})")
                    is_duplicate = True
                    break

            if not is_duplicate:
                unique_datasets.append(candidate)

        self.logger.info(f"Deduplication complete. Retained {len(unique_datasets)} unique datasets.")
        return unique_datasets