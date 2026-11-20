"""DataForge - Data Engineering: dataset integration public API."""
from .dataset_merger import DatasetMergeResult, merge_datasets
from .provenance_manager import ProvenanceResult, attach_provenance, validate_provenance
from .record_id_generator import RecordIDResult, assign_record_ids, generate_record_ids

__all__ = [
    'DatasetMergeResult', 'merge_datasets',
    'ProvenanceResult', 'attach_provenance', 'validate_provenance',
    'RecordIDResult', 'assign_record_ids', 'generate_record_ids',
]
