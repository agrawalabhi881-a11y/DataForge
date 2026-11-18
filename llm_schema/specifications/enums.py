from enum import StrEnum


class DataPreference(StrEnum):
    REAL_ONLY = "real_only"
    SYNTHETIC_ONLY = "synthetic_only"
    REAL_PREFERRED = "real_preferred"
    SYNTHETIC_PREFERRED = "synthetic_preferred"
    BOTH = "both"


class DatasetFormat(StrEnum):
    CSV = "csv"
    JSON = "json"
    PARQUET = "parquet"
