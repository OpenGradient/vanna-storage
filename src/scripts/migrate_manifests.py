import sys
import os

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.ipfs_client import IPFSClient
from core.model_repository import get_metadata
import logging

logging.basicConfig(level=logging.INFO)

def migrate_manifests():
    client = IPFSClient()
    metadata = get_metadata()
    logging.info(f"Initial metadata: {metadata}")
    
    for model_id, versions in metadata['models'].items():
        for version, manifest_cid in versions.items():
            logging.info(f"Processing {model_id} version {version}")
            manifest = client.get_json(manifest_cid)
            
            if 'model_hash' in manifest:
                logging.info(f"Updating manifest for {model_id} version {version}")
                manifest['model_cid'] = manifest.pop('model_hash')
                
                new_manifest_cid = client.add_json(manifest)
                metadata['models'][model_id][version] = new_manifest_cid
                logging.info(f"Updated manifest CID for {model_id} version {version}: {new_manifest_cid}")
            else:
                logging.info(f"Manifest for {model_id} version {version} already uses model_cid")
    
    new_metadata_cid = client.add_json(metadata)
    logging.info(f"Updated metadata stored with CID: {new_metadata_cid}")
    
    stored_metadata = client.get_json(new_metadata_cid)
    logging.info(f"Verified stored metadata: {stored_metadata}")

if __name__ == "__main__":
    migrate_manifests()