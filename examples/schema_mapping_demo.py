"""Independent local demo: python examples/schema_mapping_demo.py"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from llm_schema.mapping import compatibility_report, deterministic_mapping
from llm_schema.mapping.mapper import ColumnProfile, DatasetProfile


def main() -> None:
    profile = DatasetProfile(
        path="sample.csv",
        format="csv",
        columns=[
            ColumnProfile(name="url", data_type="object", samples=["https://example.test"]),
            ColumnProfile(name="sample_id", data_type="object", samples=["p-001"]),
            ColumnProfile(name="class", data_type="int64", samples=["1"]),
            ColumnProfile(name="unexpected", data_type="object"),
        ],
    )
    mapping = deterministic_mapping(profile, "phishing_urls")
    report = compatibility_report(profile, mapping)
    print("Mappings:", mapping.model_dump_json(indent=2))
    print("Compatibility:", report.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
