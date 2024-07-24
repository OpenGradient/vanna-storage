from typing import List
from packaging.version import parse
from .base import ModelRepository

def validate_version(self, model_id: str, new_version: str) -> bool:
    existing_versions = self.list_versions(model_id)
    if not existing_versions:
        return True
    return all(parse(new_version) > parse(v) for v in existing_versions)

def list_versions(self, model_id: str) -> List[str]:
    metadata = self._get_metadata()
    if 'models' in metadata and model_id in metadata['models']:
        versions = list(metadata['models'][model_id].keys())
        versions.sort(key=lambda v: parse(v))
        return versions
    return []

def get_latest_version(self, model_id: str) -> str:
    versions = self.list_versions(model_id)
    if not versions:
        raise ValueError(f"No versions available for model_id {model_id}")
    return versions[-1]

ModelRepository.validate_version = validate_version
ModelRepository.list_versions = list_versions
ModelRepository.get_latest_version = get_latest_version