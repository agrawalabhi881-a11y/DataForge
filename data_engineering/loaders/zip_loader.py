
"""
DataForge 
Module: ZIP Dataset Loader

Read supported datasets from ZIP archives without
extracting files to disk or modifying source archives.
"""

import io
import json
import zipfile
from pathlib import Path, PurePosixPath

import pandas as pd


SUPPORTED_FORMATS = {".csv", ".json", ".jsonl", ".parquet"}

MAX_MEMBER_SIZE = 100 * 1024 * 1024
MAX_COMPRESSION_RATIO = 100


def validate_zip_file(file_path: str | Path) -> Path:
    """Validate the ZIP archive path and format."""

    path = Path(file_path).expanduser()

    if not path.is_file():
        raise FileNotFoundError(
            f"ZIP file does not exist: {path}"
        )

    if path.suffix.lower() != ".zip":
        raise ValueError(
            f"Unsupported archive format: {path.suffix}. "
            "Expected a .zip file."
        )

    if not zipfile.is_zipfile(path):
        raise ValueError(
            f"Invalid or corrupted ZIP archive: {path}"
        )

    return path


def _is_safe_member(info: zipfile.ZipInfo) -> bool:
    """Check archive member paths and supported formats."""

    name = info.filename.replace("\\", "/")
    member_path = PurePosixPath(name)

    if info.is_dir():
        return False

    if name.startswith("/") or name.startswith("\\"):
        return False

    if ".." in member_path.parts:
        return False

    if ":" in name:
        return False

    if info.flag_bits & 0x1:
        return False

    if member_path.suffix.lower() not in SUPPORTED_FORMATS:
        return False

    return True


def _validate_member(info: zipfile.ZipInfo) -> None:
    """Enforce size and compression safety limits."""

    if not _is_safe_member(info):
        raise ValueError(
            f"Unsupported or unsafe ZIP member: {info.filename}"
        )

    if info.file_size > MAX_MEMBER_SIZE:
        raise ValueError(
            f"ZIP member exceeds 100 MB limit: {info.filename}"
        )

    if info.file_size > 0:
        ratio = info.file_size / max(info.compress_size, 1)

        if ratio > MAX_COMPRESSION_RATIO:
            raise ValueError(
                f"Suspicious compression ratio: {info.filename}"
            )


def list_zip_datasets(file_path: str | Path) -> list[str]:
    """List supported, safe dataset files in a ZIP archive."""

    path = validate_zip_file(file_path)

    with zipfile.ZipFile(path, "r") as archive:
        return [
            info.filename
            for info in archive.infolist()
            if _is_safe_member(info)
            and info.file_size <= MAX_MEMBER_SIZE
            and (
                info.file_size == 0
                or info.file_size / max(info.compress_size, 1)
                <= MAX_COMPRESSION_RATIO
            )
        ]


def _parse_dataset(
    data: bytes,
    extension: str,
) -> pd.DataFrame:
    """Convert supported archive contents into a DataFrame."""

    if extension == ".csv":
        return pd.read_csv(
            io.BytesIO(data),
            encoding="utf-8-sig",
        )

    if extension == ".parquet":
        return pd.read_parquet(
            io.BytesIO(data),
            engine="pyarrow",
        )

    if extension in {".json", ".jsonl"}:
        text = data.decode("utf-8-sig")

        if extension == ".jsonl":
            records = []

            for line_number, line in enumerate(
                text.splitlines(), start=1
            ):
                if not line.strip():
                    continue

                try:
                    record = json.loads(line)
                except json.JSONDecodeError as error:
                    raise ValueError(
                        f"Invalid JSONL at line {line_number}"
                    ) from error

                if not isinstance(record, dict):
                    raise ValueError(
                        f"JSONL line {line_number} "
                        "must contain an object."
                    )

                records.append(record)

        else:
            document = json.loads(text)

            if isinstance(document, list):
                records = document

            elif isinstance(document, dict):
                if "records" in document:
                    records = document["records"]
                elif "data" in document:
                    records = document["data"]
                else:
                    raise ValueError(
                        "JSON must contain a records or data array."
                    )
            else:
                raise ValueError(
                    "Unsupported JSON dataset structure."
                )

        if not isinstance(records, list) or not all(
            isinstance(record, dict) for record in records
        ):
            raise ValueError(
                "Dataset must contain a list of JSON objects."
            )

        return pd.DataFrame.from_records(records)

    raise ValueError(
        f"Unsupported dataset format: {extension}"
    )


def load_zip_dataset(
    file_path: str | Path,
    member_name: str | None = None,
) -> pd.DataFrame:
    """
    Load one supported dataset from a ZIP archive.

    If member_name is omitted, exactly one supported
    dataset must be present.
    """

    path = validate_zip_file(file_path)

    with zipfile.ZipFile(path, "r") as archive:
        available = list_zip_datasets(path)

        if member_name is None:
            if len(available) != 1:
                raise ValueError(
                    "Specify member_name when the archive "
                    "contains zero or multiple datasets."
                )
            member_name = available[0]

        if member_name not in available:
            raise ValueError(
                f"Dataset not available or unsafe: {member_name}"
            )

        matches = [
            info for info in archive.infolist()
            if info.filename == member_name
        ]

        if len(matches) != 1:
            raise ValueError(
                f"Ambiguous ZIP member name: {member_name}"
            )

        info = matches[0]
        _validate_member(info)

        try:
            with archive.open(info, "r") as member:
                data = member.read(MAX_MEMBER_SIZE + 1)

        except (OSError, RuntimeError, zipfile.BadZipFile) as error:
            raise ValueError(
                f"Unable to read ZIP member: {member_name}"
            ) from error

        if len(data) > MAX_MEMBER_SIZE:
            raise ValueError(
                f"ZIP member exceeds size limit: {member_name}"
            )

    extension = PurePosixPath(
        member_name.replace("\\", "/")
    ).suffix.lower()

    return _parse_dataset(data, extension)


def extract_zip_metadata(
    file_path: str | Path,
    member_name: str,
    dataframe: pd.DataFrame,
) -> dict:
    """Extract archive and loaded dataset metadata."""

    path = validate_zip_file(file_path)

    with zipfile.ZipFile(path, "r") as archive:
        matches = [
            info for info in archive.infolist()
            if info.filename == member_name
        ]

        if len(matches) != 1:
            raise ValueError(
                f"ZIP member not found or ambiguous: {member_name}"
            )

        info = matches[0]
        _validate_member(info)

        return {
            "archive_name": path.name,
            "archive_size_bytes": path.stat().st_size,
            "member_name": member_name,
            "file_format": PurePosixPath(
                member_name.replace("\\", "/")
            ).suffix.lower().lstrip("."),
            "member_size_bytes": info.file_size,
            "compressed_size_bytes": info.compress_size,
            "record_count": int(len(dataframe)),
            "column_count": int(len(dataframe.columns)),
            "columns": dataframe.columns.tolist(),
            "data_types": {
                column: str(dtype)
                for column, dtype in dataframe.dtypes.items()
            },
            "missing_values": {
                column: int(count)
                for column, count
                in dataframe.isna().sum().items()
            },
        }
