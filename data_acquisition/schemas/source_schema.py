from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime

class DatasetMetadata(BaseModel):
    """
    Standardized schema for dataset metadata ingested across 
    Phishing, Attack Logs, Code Vulnerabilities, and User Behavior domains.
    """
    dataset_id: str = Field(..., description="Unique identifier for the dataset.")
    source_platform: str = Field(..., description="Platform origin (e.g., Kaggle, HuggingFace, Custom).")
    domain: str = Field(..., description="Core domain category (phishing, attack_logs, code_vuln, user_behavior).")
    title: str = Field(..., description="Name or title of the dataset.")
    description: Optional[str] = Field(None, description="Detailed description of the data contents.")
    version: str = Field(default="1.0.0", description="Dataset version.")
    record_count: Optional[int] = Field(None, description="Number of records or rows in the dataset.")
    file_path: Optional[str] = Field(None, description="Local or remote storage path where raw files reside.")
    tags: List[str] = Field(default_factory=list, description="Associated cybersecurity tags.")
    ingested_at: datetime = Field(default_factory=datetime.utcnow, description="Timestamp of ingestion.")
    extra_metadata: Dict[str, Any] = Field(default_factory=dict, description="Platform-specific flexible attributes.")