# initialize_repo.py
from src.model_repository import ModelRepository
from src.config import ENV

if __name__ == "__main__":
    if ENV == 'production':
        confirmation = input("WARNING: You are about to initialize production metadata. Are you sure? (yes/no): ")
        if confirmation.lower() != 'yes':
            print("Initialization cancelled.")
            exit(1)
    elif ENV == 'staging':
        print("Initializing staging environment metadata.")
    else:
        print("Initializing local environment metadata.")
    
    repo = ModelRepository()
    repo.initialize_metadata(force=True)
    print(f"Repository initialized successfully for {ENV} environment.")