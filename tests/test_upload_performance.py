import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'src'))

import unittest
import time
import random
import string
import io
from src.core.model_repository import ModelRepository
from src.core.ipfs_client import IPFSClient
from uuid import uuid4

def generate_random_file(size):
    return io.BytesIO(random.randbytes(size))

class TestUploadPerformance(unittest.TestCase):
    def setUp(self):
        self.repo = ModelRepository()
        self.ipfs_client = IPFSClient()

    def test_upload_performance(self):
        file_sizes = [10 * 1024 * 1024, 100 * 1024 * 1024, 500 * 1024 * 1024, 1024 * 1024 * 1024, 2 * 1024 * 1024 * 1024]
        results = []

        for size in file_sizes:
            file_content = generate_random_file(size)
            file_name = f"test_file_{size}.bin"
            
            start_time = time.time()
            manifest_cid, version = self.repo.upload_model(uuid4(), {file_name: file_content}, None, "Test upload", False)
            end_time = time.time()
            
            upload_time = end_time - start_time
            results.append((size, upload_time))
            
            print(f"File size: {size / (1024 * 1024):.2f} MB, Upload time: {upload_time:.2f} seconds")

        # You can save these results to a file or plot them using matplotlib
        return results

if __name__ == '__main__':
    unittest.main()