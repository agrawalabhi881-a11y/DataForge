import pandas as pd
import pytest
from pathlib import Path
from data_acquisition.services.modeling_service import ModelingService

def test_modeling_service_lightgbm(tmp_path):
    """Test LightGBM model training on synthetic processed classification data."""
    processed_dir = tmp_path / "processed"
    processed_dir.mkdir(parents=True, exist_ok=True)
    
    # Create sample processed dataset (resembling Iris structure)
    df = pd.DataFrame({
        "sepal_length": [5.1, 4.9, 4.7, 4.6, 5.0, 5.4, 4.6, 5.0, 4.4, 4.9],
        "sepal_width": [3.5, 3.0, 3.2, 3.1, 3.6, 3.9, 3.4, 3.4, 2.9, 3.1],
        "petal_length": [1.4, 1.4, 1.3, 1.5, 1.4, 1.7, 1.4, 1.5, 1.4, 1.5],
        "petal_width": [0.2, 0.2, 0.2, 0.2, 0.2, 0.4, 0.3, 0.2, 0.2, 0.1],
        "species": [0, 0, 0, 0, 0, 1, 1, 1, 1, 1]
    })
    
    filename = "test_iris_processed.csv"
    df.to_csv(processed_dir / filename, index=False)

    service = ModelingService(base_dir=str(tmp_path))
    model, accuracy = service.train_lightgbm_classifier(
        processed_filename=filename,
        target_column="species",
        test_size=0.3
    )

    assert model is not None
    assert 0.0 <= accuracy <= 1.0
    assert (tmp_path / "models" / "lgbm_model.txt").exists()