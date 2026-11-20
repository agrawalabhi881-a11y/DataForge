"""Shared DataForge fixtures."""
import pandas as pd
import pytest

@pytest.fixture
def phishing_frame():
    return pd.DataFrame({"url": ["https://example.com", "https://example.org", "https://example.net"], "label": ["benign", "benign", "malicious"]})
