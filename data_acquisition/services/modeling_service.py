import logging
import pandas as pd
from pathlib import Path
from typing import Tuple, Optional
import lightgbm as lgb
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, mean_squared_error

logger = logging.getLogger(__name__)

class ModelingService:
    """
    Orchestrates feature extraction, dataset splitting, and LightGBM model training
    on processed datasets.
    """

    def __init__(self, base_dir: str = "data"):
        self.base_dir = Path(base_dir)
        self.processed_dir = self.base_dir / "processed"
        self.models_dir = self.base_dir / "models"
        self.models_dir.mkdir(parents=True, exist_ok=True)
        self.logger = logging.getLogger(self.__class__.__name__)

    def train_lightgbm_classifier(
        self, 
        processed_filename: str, 
        target_column: str, 
        test_size: float = 0.2
    ) -> Optional[Tuple[lgb.Booster, float]]:
        """
        Trains a LightGBM classifier on a processed dataset.
        """
        file_path = self.processed_dir / processed_filename
        
        if not file_path.exists():
            self.logger.error(f"Processed file not found at: {file_path}")
            return None

        self.logger.info(f"Loading processed data from {file_path} for modeling...")
        df = pd.read_csv(file_path)

        if target_column not in df.columns:
            self.logger.error(f"Target column '{target_column}' not found in dataset.")
            return None

        # Split features and target
        X = df.drop(columns=[target_column])
        y = df[target_column]

        # Handle categorical variables if any exist
        for col in X.select_dtypes(include=["object", "category"]).columns:
            X[col] = X[col].astype("category")

        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=test_size, random_state=42
        )

        self.logger.info("Training LightGBM model...")
        
        # Configure LightGBM dataset and parameters
        train_data = lgb.Dataset(X_train, label=y_train)
        valid_data = lgb.Dataset(X_test, label=y_test, reference=train_data)

        params = {
            "objective": "multiclass",
            "num_class": len(y.unique()),
            "metric": "multi_logloss",
            "boosting_type": "gbdt",
            "learning_rate": 0.05,
            "verbose": -1
        }

        model = lgb.train(
            params,
            train_data,
            num_boost_round=100,
            valid_sets=[valid_data]
        )

        # Evaluate
        preds = model.predict(X_test)
        pred_labels = preds.argmax(axis=1)
        accuracy = accuracy_score(y_test, pred_labels)
        
        self.logger.info(f"Model training completed successfully! Test Accuracy: {accuracy:.4f}")

        # Save model artifact
        model_path = self.models_dir / "lgbm_model.txt"
        model.save_model(str(model_path))
        self.logger.info(f"Model saved to {model_path}")

        return model, accuracy