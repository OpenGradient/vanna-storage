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
from src.core.model_repository import get_metadata

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

def test_upload_model(client):
    model_id = f"test_onnx_model_{int(time.time())}"
    with open("tests/mock_onnx/test_model.onnx", "rb") as f:
        files = {"file": ("test_model.onnx", f)}
        data = {"model_id": model_id, "version": "1.00"}  # Changed from "1.0" to "1.00"
        response = client.post("/upload_model", files=files, data=data)

    print(f"Response status code: {response.status_code}")
    print(f"Response content: {response.content}")

    assert response.status_code == 200
    response_json = response.json()
    assert "manifest_cid" in response_json
    print(f"Manifest CID: {response_json['manifest_cid']}")

    # Immediately check the metadata
    metadata = get_metadata()
    print(f"Immediate metadata check: {json.dumps(metadata, indent=2)}")

    assert model_id in metadata["models"], "Model not found in metadata"
    assert "versions" in metadata["models"][model_id], "Versions not found in metadata"
    assert "1.00" in metadata["models"][model_id]["versions"], "Version 1.00 not found in metadata"
    assert metadata["models"][model_id]["versions"]["1.00"] == response_json["manifest_cid"], \
        f"Manifest CID mismatch. Expected: {response_json['manifest_cid']}, " \
        f"Actual: {metadata['models'][model_id]['versions']['1.00']}"

    print("Metadata updated successfully!")

def test_inspect_manifest(client):
    model_id = f"test_content_model_{int(time.time())}"
    # First, upload a model
    with open("tests/mock_onnx/test_model.onnx", "rb") as f:
        files = {"file": ("test_model.onnx", f)}
        data = {"model_id": model_id, "version": "1.00"}  # Changed from "1.0" to "1.00"
        response = client.post("/upload_model", files=files, data=data)
    
    assert response.status_code == 200
    
    # Now, inspect manifest for this model
    inspect_manifest_response = client.get(f"/inspect_manifest/{model_id}/1.00")  # Changed from "1.0" to "1.00"

    print(f"Inspect manifest response status: {inspect_manifest_response.status_code}")
    print(f"Inspect manifest response content: {inspect_manifest_response.text}")

    assert inspect_manifest_response.status_code == 200, f"Inspect manifest failed with status {inspect_manifest_response.status_code}: {inspect_manifest_response.text}"
    content = inspect_manifest_response.json()
    
    print(f"Inspected content: {json.dumps(content, indent=2)}")
    
    assert "metadata_manifest_cid" in content
    assert "manifest_content" in content
    assert "model_id" in content["manifest_content"]
    assert "version" in content["manifest_content"]