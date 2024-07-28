import httpx
import pytest
import json
import time
import requests
from requests.exceptions import RequestException

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
        data = {"model_id": model_id, "version": "1.0"}
        response = client.post("/upload_model", files=files, data=data)

    print(f"Response status code: {response.status_code}")
    print(f"Response content: {response.content}")

    assert response.status_code == 200
    response_json = response.json()
    assert "manifest_cid" in response_json
    print(f"Manifest CID: {response_json['manifest_cid']}")

    # Immediately check the metadata
    metadata_response = client.get("/get_metadata")
    assert metadata_response.status_code == 200
    metadata = metadata_response.json()
    print(f"Immediate metadata check: {json.dumps(metadata, indent=2)}")

    assert model_id in metadata["models"], "Model not found in metadata"
    assert "versions" in metadata["models"][model_id], "Versions not found in metadata"
    assert "1.0" in metadata["models"][model_id]["versions"], "Version 1.0 not found in metadata"
    assert metadata["models"][model_id]["versions"]["1.0"] == response_json["manifest_cid"], \
        f"Manifest CID mismatch. Expected: {response_json['manifest_cid']}, " \
        f"Actual: {metadata['models'][model_id]['versions']['1.0']}"

    print("Metadata updated successfully!")

def test_list_versions(client):
    model_id = f"test_list_model_{int(time.time())}"
    # First, upload a model (version 1.0)
    with open("tests/mock_onnx/test_model.onnx", "rb") as f:
        files = {"file": ("test_model.onnx", f)}
        data = {"model_id": model_id, "version": "1.0"}
        response = client.post("/upload_model", files=files, data=data)

    assert response.status_code == 200, f"Upload failed with status {response.status_code}: {response.text}"
    print(f"Upload response for version 1.0: {response.json()}")

    # Upload another version (2.0)
    with open("tests/mock_onnx/test_model.onnx", "rb") as f:
        files = {"file": ("test_model.onnx", f)}
        data = {"model_id": model_id, "version": "2.0"}
        response = client.post("/upload_model", files=files, data=data)

    assert response.status_code == 200, f"Upload of version 2.0 failed with status {response.status_code}: {response.text}"
    print(f"Upload response for version 2.0: {response.json()}")

    # Get metadata to check versions
    metadata_response = client.get("/get_metadata")
    assert metadata_response.status_code == 200
    metadata = metadata_response.json()
    print(f"Full metadata after uploads: {json.dumps(metadata, indent=2)}")

    # Now, list versions for this model
    list_versions_response = client.get("/get_versions", params={"model_id": model_id})

    print(f"List versions response status: {list_versions_response.status_code}")
    print(f"List versions response content: {list_versions_response.text}")

    assert list_versions_response.status_code == 200, f"List versions failed with status {list_versions_response.status_code}: {list_versions_response.text}"
    versions = list_versions_response.json()
    assert isinstance(versions, list), f"Expected a list of versions, got {type(versions)}"
    assert "1.0" in versions, f"Expected version 1.0 in {versions}"
    assert "2.0" in versions, f"Expected version 2.0 in {versions}"

    print(f"Listed versions: {versions}")

def test_inspect_manifest(client):
    model_id = f"test_content_model_{int(time.time())}"
    # First, upload a model
    with open("tests/mock_onnx/test_model.onnx", "rb") as f:
        files = {"file": ("test_model.onnx", f)}
        data = {"model_id": model_id, "version": "1.0"}
        response = client.post("/upload_model", files=files, data=data)
    
    assert response.status_code == 200
    
    # Now, inspect manifest for this model
    inspect_manifest_response = client.get("/inspect_manifest", params={"model_id": model_id, "version": "1.0"})

    print(f"Inspect manifest response status: {inspect_manifest_response.status_code}")
    print(f"Inspect manifest response content: {inspect_manifest_response.text}")

    assert inspect_manifest_response.status_code == 200, f"Inspect manifest failed with status {inspect_manifest_response.status_code}: {inspect_manifest_response.text}"
    content = inspect_manifest_response.json()
    
    print(f"Inspected content: {json.dumps(content, indent=2)}")
    
    assert "model_id" in content
    assert "version" in content
    assert "manifest_cid" in content