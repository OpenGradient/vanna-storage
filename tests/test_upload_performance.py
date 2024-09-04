import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'src'))

import unittest
import time
import io
from src.core.model_repository import ModelRepository
from src.core.ipfs_client import IPFSClient
from uuid import uuid4
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class RandomDataGenerator(io.RawIOBase):
    def __init__(self, size):
        self.size = size
        self.remaining = size

    def read(self, n=-1):
        if self.remaining == 0:
            return b''
        if n == -1:
            n = self.remaining
        data = os.urandom(min(n, self.remaining))
        self.remaining -= len(data)
        return data

    def readable(self):
        return True

class TestUploadPerformance(unittest.TestCase):
    def setUp(self):
        print("Setting up TestUploadPerformance")
        self.repo = ModelRepository()

    def upload_and_measure(self, size):
        print(f"Starting upload_and_measure for size: {size}")
        ipfs_uuid = uuid4()
        file_name = f"test_file_{size}.bin"
        file_content = RandomDataGenerator(size)
        
        try:
            start_time = time.time()
            manifest_cid, version = self.repo.upload_model(
                ipfs_uuid=ipfs_uuid,
                new_files={file_name: file_content},
                existing_files=None,
                release_notes="Test upload",
                is_major_version=False
            )
            end_time = time.time()
            
            upload_time = end_time - start_time
            print(f"File size: {size / (1024 * 1024):.2f} MB")
            print(f"Upload time: {upload_time:.2f} seconds")
            print(f"IPFS UUID: {ipfs_uuid}")
            print(f"Manifest CID: {manifest_cid}")
            print(f"Version: {version}")
            print("-" * 50)
            return size, upload_time, ipfs_uuid, manifest_cid, version
        except Exception as e:
            print(f"Error during upload: {str(e)}")
            raise

    def test_upload_performance(self):
        print("Starting test_upload_performance")
        file_sizes = [
            1 * 1024 * 1024,         # 1 MB
            10 * 1024 * 1024,        # 10 MB
            100 * 1024 * 1024,       # 100 MB
            1024 * 1024 * 1024,      # 1 GB
            5 * 1024 * 1024 * 1024,  # 5 GB
            10 * 1024 * 1024 * 1024, # 10 GB
            20 * 1024 * 1024 * 1024  # 20 GB
        ]

        results = []
        for size in file_sizes:
            try:
                print(f"Testing upload for size: {size / (1024 * 1024):.2f} MB")
                size, upload_time, ipfs_uuid, manifest_cid, version = self.upload_and_measure(size)
                results.append({
                    'size': size,
                    'upload_time': upload_time,
                    'ipfs_uuid': ipfs_uuid,
                    'manifest_cid': manifest_cid,
                    'version': version
                })
                self.assertIsNotNone(upload_time)
            except Exception as e:
                print(f"Failed to upload file of size {size / (1024 * 1024):.2f} MB: {str(e)}")
                import traceback
                traceback.print_exc()

        print("\nSummary of all uploads:")
        for result in results:
            print(f"Size: {result['size'] / (1024 * 1024):.2f} MB, "
                  f"Time: {result['upload_time']:.2f} s, "
                  f"UUID: {result['ipfs_uuid']}, "
                  f"CID: {result['manifest_cid']}, "
                  f"Version: {result['version']}")

if __name__ == '__main__':
    unittest.main()