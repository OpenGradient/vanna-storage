from typing import Dict, List
import logging

logger = logging.getLogger(__name__)

class ModelRepository:
    _instance = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        if self._instance is not None:
            raise ValueError("An instantiation already exists!")
        self._instance = self
        self.metadata_cid = None
        self.initialize_metadata()

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