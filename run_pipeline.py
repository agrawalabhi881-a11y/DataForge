import logging
from data_acquisition.services.ingestion_service import IngestionService
from data_acquisition.services.processing_service import ProcessingService

# Configure logging to monitor pipeline progress
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("DataForgePipeline")

def main():
    logger.info("Starting DataForge End-to-End Pipeline...")

    # 1. Initialize Services
    ingestion_service = IngestionService()
    processing_service = ProcessingService()

    # 2. Ingest Dataset (Using 'uciml/iris' as our verified open dataset)
    dataset_ref = "uciml/iris"
    domain = "botany"
    
    logger.info(f"Step 1: Ingesting dataset '{dataset_ref}'...")
    metadata = ingestion_service.ingest_kaggle_dataset(dataset_ref=dataset_ref, domain=domain)
    
    if not metadata:
        logger.error("Pipeline aborted: Ingestion failed.")
        return

    logger.info(f"Successfully ingested to: {metadata.file_path}")

    # 3. Process/Clean Dataset
    # Kaggle downloads iris dataset into a folder structure with 'iris.csv'
    dataset_folder_name = dataset_ref.replace("/", "_")
    filename = "iris.csv"  # standard filename for uciml/iris
    
    logger.info(f"Step 2: Processing dataset '{dataset_folder_name}/{filename}'...")
    processed_path = processing_service.process_csv_dataset(
        dataset_name=dataset_folder_name, 
        filename=filename
    )

    if processed_path:
        logger.info(f"Pipeline Completed Successfully! Processed file saved at: {processed_path}")
    else:
        logger.error("Pipeline failed during processing step.")

if __name__ == "__main__":
    main()