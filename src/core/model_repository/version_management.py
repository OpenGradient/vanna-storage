from typing import List
from packaging.version import parse
from .metadata import get_metadata

def validate_version(model_id: str, new_version: str) -> bool:
    from .metadata import get_metadata
    metadata = get_metadata()
    
    if model_id not in metadata['models']:
        return True  # New model, any version is valid
    
    model_versions = metadata['models'][model_id].get('versions', {})
    if not model_versions:
        return True  # No existing versions, any version is valid
    
    existing_versions = list(model_versions.keys())
    
    return all(parse(new_version) > parse(v) for v in existing_versions)

def list_versions(model_id: str) -> List[str]:
    metadata = get_metadata()
    return list(metadata.get('models', {}).get(model_id, {}).keys())

def get_latest_version(model_id: str) -> str:
    versions = list_versions(model_id)
    if not versions:
        raise ValueError(f"No versions available for model_id {model_id}")
    return max(versions, key=lambda v: parse(v))