from typing import List
from packaging.version import parse
from .metadata import get_metadata

from packaging import version

def validate_version(model_id: str, new_version: str) -> bool:
    metadata = get_metadata()
    if model_id not in metadata['models']:
        return True
    existing_versions = metadata['models'][model_id].get('versions', {}).keys()
    return all(version.parse(new_version) > version.parse(v) for v in existing_versions)

def list_versions(model_id: str) -> List[str]:
    metadata = get_metadata()
    return list(metadata.get('models', {}).get(model_id, {}).keys())

def get_latest_version(model_id: str) -> str:
    versions = list_versions(model_id)
    if not versions:
        raise ValueError(f"No versions available for model_id {model_id}")
    return max(versions, key=lambda v: parse(v))

def get_versions(model_id):
    metadata = get_metadata()
    if model_id not in metadata['models']:
        return []
    return list(metadata['models'][model_id]['versions'].keys())

def inspect_manifest(model_id, version):
    metadata = get_metadata()
    if model_id not in metadata['models'] or version not in metadata['models'][model_id]['versions']:
        return None
    manifest_cid = metadata['models'][model_id]['versions'][version]
    # Fetch and return the manifest content from IPFS
    # You'll need to implement this part based on your IPFS client
    return {"model_id": model_id, "version": version, "manifest_cid": manifest_cid}