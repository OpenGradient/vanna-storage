from typing import List
from packaging.version import parse
from .metadata import get_metadata

def validate_version(model_id: str, new_version: str) -> bool:
    existing_versions = list_versions(model_id)
    if not existing_versions:
        return True
    return all(parse(new_version) > parse(v) for v in existing_versions)

def list_versions(model_id: str) -> List[str]:
    metadata = get_metadata()
    return list(metadata.get('models', {}).get(model_id, {}).keys())

def get_latest_version(model_id: str) -> str:
    versions = list_versions(model_id)
    if not versions:
        raise ValueError(f"No versions available for model_id {model_id}")
    return max(versions, key=lambda v: parse(v))