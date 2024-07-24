from .base import ModelRepository
from core.ipfs_client import IPFSClient

def download_model(self, model_id: str, version: str) -> bytes:
    client = IPFSClient()
    manifest_cid = self.get_manifest_cid(model_id, version)
    if not manifest_cid:
        raise ValueError(f"No manifest found for model {model_id} version {version}")
    
    manifest = client.get_json(manifest_cid)
    model_hash = manifest['model_hash']
    model_data = client.cat(model_hash)
    return model_data

ModelRepository.download_model = download_model