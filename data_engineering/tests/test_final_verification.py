"""DataForge additional regression checks for loading, cleaning and domains."""
import pandas as pd
import pytest


def test_csv_loader_roundtrip(tmp_path):
    from data_engineering.loaders.csv_loader import load_csv
    source = pd.DataFrame({'url': ['https://example.com'], 'label': ['benign']})
    path = tmp_path / 'sample.csv'
    source.to_csv(path, index=False)
    result = load_csv(path)
    frame = result.dataframe if hasattr(result, 'dataframe') else result
    assert len(frame) == 1
    assert frame['label'].iloc[0] == 'benign'


def test_json_loader_roundtrip(tmp_path):
    from data_engineering.loaders.json_loader import load_json
    path = tmp_path / 'sample.json'
    path.write_text('[{"url":"https://example.com","label":"benign"}]', encoding='utf-8')
    result = load_json(path)
    frame = result.dataframe if hasattr(result, 'dataframe') else result
    assert len(frame) == 1


def test_parquet_loader_roundtrip(tmp_path):
    from data_engineering.loaders.parquet_loader import load_parquet
    source = pd.DataFrame({'label': ['benign', 'malicious']})
    path = tmp_path / 'sample.parquet'
    source.to_parquet(path, index=False)
    result = load_parquet(path)
    frame = result.dataframe if hasattr(result, 'dataframe') else result
    assert frame['label'].tolist() == ['benign', 'malicious']


def test_string_normalization_preserves_source():
    from data_engineering.cleaning.string_normalization import normalize_strings
    source = pd.DataFrame({'url': [' https://example.com/Admin ']})
    result = normalize_strings(source)
    assert result.dataframe['url'].iloc[0] == 'https://example.com/Admin'
    assert source['url'].iloc[0] == ' https://example.com/Admin '


def test_outlier_detection_flags_without_deleting():
    from data_engineering.cleaning.outlier_detection import detect_outliers
    source = pd.DataFrame({'requests': [10, 11, 12, 13, 14, 1000]})
    result = detect_outliers(source, columns=['requests'])
    assert len(result.dataframe) == len(source)
    assert bool(result.dataframe['requests_is_outlier'].iloc[-1])
    assert len(result.outlier_records) == 1


def test_phishing_flags_invalid_url():
    from data_engineering.domain_processing.phishing import process_phishing
    source = pd.DataFrame({'url': ['https://example.com/login', 'invalid']})
    result = process_phishing(source)
    assert result.statistics['invalid_urls'] == 1
    assert source.columns.tolist() == ['url']


def test_attack_logs_flags_invalid_records():
    from data_engineering.domain_processing.attack_logs import process_attack_logs
    source = pd.DataFrame({'timestamp': ['2026-01-01', 'invalid'], 'source_ip': ['127.0.0.1', 'invalid']})
    result = process_attack_logs(source)
    assert result.statistics['invalid_records'] == 1


def test_vulnerable_code_accepts_valid_line():
    from data_engineering.domain_processing.vulnerable_code import process_vulnerable_code
    source = pd.DataFrame({'code_snippet': ['x = 1\ny = 2'], 'cwe_id': ['CWE-79'], 'vulnerable_lines': ['2']})
    result = process_vulnerable_code(source)
    assert result.statistics['invalid_records'] == 0


def test_user_behavior_accepts_valid_session():
    from data_engineering.domain_processing.user_behavior import process_user_behavior
    source = pd.DataFrame({'user_id': ['u1'], 'timestamp': ['2026-01-01'], 'session_id': ['s1']})
    result = process_user_behavior(source)
    assert result.statistics['invalid_records'] == 0
