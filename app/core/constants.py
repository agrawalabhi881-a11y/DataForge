"""Shared allowed values. Agree on these with the team before changing them."""

DOMAINS = ("phishing", "attack_logs", "vulnerable_code", "user_behavior")
STRATEGIES = ("real_only", "real_plus_synthetic", "synthetic_only")
REQUEST_STATUSES = ("pending", "processing", "completed", "failed", "cancelled")
JOB_STATUSES = ("pending", "running", "completed", "failed", "retrying", "cancelled")
SOURCE_TYPES = ("real", "synthetic", "mixed")
FILE_FORMATS = ("csv", "json", "jsonl", "parquet", "xlsx")
LICENSE_STATUSES = ("unverified", "verified_open", "restricted")
ACQUISITION_METHODS = ("api", "direct_download", "scraping")
GENERATION_METHODS = ("rule_based", "llm_based", "hybrid")
DATASET_STAGES = ("raw", "processed", "synthetic", "final")
QUALITY_STATUSES = ("pending", "validated", "failed")
VALIDATION_STATUSES = ("pending", "valid", "invalid")