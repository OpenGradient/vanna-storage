from typing import Dict, List
import logging

from core.ipfs_client import IPFSClient

logger = logging.getLogger(__name__)

class ModelRepository:
    _instance = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        self._instance = self
        self.metadata_cid = None
        self.initialize_metadata()

    def initialize_metadata(self):
        if self.metadata_cid is None:
            client = IPFSClient()
            initial_metadata = {"models": {}, "version": "1.0"}
            self.metadata_cid = self._store_metadata(initial_metadata)
            logging.info(f"Initialized new metadata with CID: {self.metadata_cid}")
        else:
            logging.info("Metadata already initialized")


    @staticmethod
    def extract_hash(result):
        if isinstance(result, str):
            return result
        elif isinstance(result, dict) and 'Hash' in result:
            return result['Hash']
        elif hasattr(result, 'get'):
            return result.get('Hash', str(result))
        else:
            return str(result)