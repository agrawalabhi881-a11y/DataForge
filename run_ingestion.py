import logging
from data_acquisition.services.ingestion_service import IngestionService

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)

def main():
    print("Initializing DataForge Ingestion Service...")
    service = IngestionService()
    
    dataset_ref = "uciml/iris"
    domain = "botany"
    
    print(f"Starting ingestion for dataset: {dataset_ref} (Domain: {domain})")
    metadata = service.ingest_kaggle_dataset(dataset_ref=dataset_ref, domain=domain)
    
    if metadata:
        print("\n--- Ingestion Successful! ---")
        print(f"Dataset ID : {metadata.dataset_id}")
        print(f"Platform   : {metadata.source_platform}")
        print(f"Domain     : {metadata.domain}")
        print(f"Saved Path : {metadata.file_path}")
        print(f"Version    : {metadata.version}")
    else:
        print("\n--- Ingestion Failed. Check logs above for details. ---")

if __name__ == "__main__":
    main()