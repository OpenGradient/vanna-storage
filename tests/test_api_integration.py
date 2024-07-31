import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'src'))

import httpx
import pytest
import json
import time
import requests
from requests.exceptions import RequestException
from src.core.model_repository import ModelRepository

BASE_URL = "http://localhost:5002"
IPFS_URL = "http://localhost:5001/api/v0"  # Adjust this if your IPFS URL is different

def wait_for_ipfs(timeout=30):
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            response = requests.post(f"{IPFS_URL}/id")
            print(f"IPFS response status: {response.status_code}")
            print(f"IPFS response content: {response.text}")
            if response.status_code == 200:
                print("IPFS is available")
                return
        except RequestException as e:
            print(f"Error connecting to IPFS: {str(e)}")
        time.sleep(1)
    pytest.fail(f"IPFS did not become available in time. Last error: {str(e) if 'e' in locals() else 'Unknown'}")

@pytest.fixture(scope="session", autouse=True)
def setup_test_env():
    wait_for_ipfs()
    yield

@pytest.fixture
def client():
    return httpx.Client(base_url=BASE_URL)

class TestModelRepository:
    
    def test_upload_model(self, client):
        model_id = f"test_onnx_model_{int(time.time())}"
        with open("tests/mock_onnx/test_model.onnx", "rb") as f:
            files = {"file": ("test_model.onnx", f)}
            data = {"model_id": model_id, "version": "1.00"}
            response = client.post("/upload_model", files=files, data=data)

        assert response.status_code == 200
        response_json = response.json()
        assert "manifest_cid" in response_json

        # Immediately check the metadata
        metadata = ModelRepository().get_metadata()  # Adjusted to call the method directly
        assert model_id in metadata["models"], "Model not found in metadata"
        assert "versions" in metadata["models"][model_id], "Versions not found in metadata"
        assert "1.00" in metadata["models"][model_id]["versions"], "Version 1.00 not found in metadata"
        assert metadata["models"][model_id]["versions"]["1.00"] == response_json["manifest_cid"], \
            f"Manifest CID mismatch. Expected: {response_json['manifest_cid']}, " \
            f"Actual: {metadata['models'][model_id]['versions']['1.00']}"