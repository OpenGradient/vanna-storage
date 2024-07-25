import httpx
import pytest
import json
import time

BASE_URL = "http://localhost:5002"

@pytest.fixture
def client():
    return httpx.Client(base_url=BASE_URL)

def test_upload_model(client):
    with open("tests/mock_onnx/test_model.onnx", "rb") as f:
        files = {"file": ("test_model.onnx", f)}
        data = {"model_id": "test_onnx_model", "version": "1.0"}
        response = client.post("/upload_model", files=files, data=data)

    print(f"Response status code: {response.status_code}")
    print(f"Response content: {response.content}")

    assert response.status_code == 200
    response_json = response.json()
    assert "manifest_cid" in response_json
    print(f"Manifest CID: {response_json['manifest_cid']}")

    # Add a retry mechanism for checking metadata
    max_retries = 5
    retry_delay = 1
    for i in range(max_retries):
        metadata_response = client.get("/get_metadata")
        assert metadata_response.status_code == 200
        metadata = metadata_response.json()
        print(f"Metadata (attempt {i+1}): {json.dumps(metadata, indent=2)}")

        if "models" in metadata and "test_onnx_model" in metadata["models"]:
            break
        time.sleep(retry_delay)
    else:
        pytest.fail("Metadata was not updated after multiple attempts")

    assert "models" in metadata
    assert "test_onnx_model" in metadata["models"]
    assert "1.0" in metadata["models"]["test_onnx_model"]
    assert metadata["models"]["test_onnx_model"]["1.0"] == response_json["manifest_cid"]

def test_list_versions(client):
    # First, upload a model (version 1.0)
    with open("tests/mock_onnx/test_model.onnx", "rb") as f:
        files = {"file": ("test_model.onnx", f)}
        data = {"model_id": "test_list_model", "version": "1.0"}
        response = client.post("/upload_model", files=files, data=data)

    assert response.status_code == 200, f"Upload failed with status {response.status_code}: {response.text}"
    print(f"Upload response for version 1.0: {response.json()}")

    # Upload another version (2.0)
    with open("tests/mock_onnx/test_model.onnx", "rb") as f:
        files = {"file": ("test_model.onnx", f)}
        data = {"model_id": "test_list_model", "version": "2.0"}
        response = client.post("/upload_model", files=files, data=data)

    assert response.status_code == 200, f"Upload of version 2.0 failed with status {response.status_code}: {response.text}"
    print(f"Upload response for version 2.0: {response.json()}")

    # Get metadata to check versions
    metadata_response = client.get("/get_metadata")
    assert metadata_response.status_code == 200
    metadata = metadata_response.json()
    print(f"Full metadata after uploads: {json.dumps(metadata, indent=2)}")

    # Now, list versions for this model
    list_versions_response = client.get("/list_versions", params={"model_id": "test_list_model"})

    print(f"List versions response status: {list_versions_response.status_code}")
    print(f"List versions response content: {list_versions_response.text}")

    assert list_versions_response.status_code == 200, f"List versions failed with status {list_versions_response.status_code}: {list_versions_response.text}"

    versions = list_versions_response.json()
    assert isinstance(versions, list), f"Expected a list of versions, got {type(versions)}"
    assert "1.0" in versions, f"Expected version 1.0 in {versions}"
    assert "2.0" in versions, f"Expected version 2.0 in {versions}"

    print(f"Listed versions: {versions}")

    # Restart the client to simulate a new session
    new_client = httpx.Client(base_url=BASE_URL)

    # List versions again with the new client
    list_versions_response = new_client.get("/list_versions", params={"model_id": "test_list_model"})
    assert list_versions_response.status_code == 200
    versions = list_versions_response.json()

    print(f"Listed versions after client restart: {versions}")

    assert isinstance(versions, list)
    assert "1.0" in versions
    assert "2.0" in versions

    new_client.close()  # Close the new client only once

def test_list_content(client):
    # First, upload a model
    with open("tests/mock_onnx/test_model.onnx", "rb") as f:
        files = {"file": ("test_model.onnx", f)}
        data = {"model_id": "test_content_model", "version": "1.0"}
        response = client.post("/upload_model", files=files, data=data)
    
    assert response.status_code == 200
    
    # Now, list content for this model
    list_content_response = client.get("/list_content", params={"model_id": "test_content_model", "version": "1.0"})
    
    assert list_content_response.status_code == 200
    content = list_content_response.json()
    
    print(f"Listed content: {json.dumps(content, indent=2)}")
    
    assert "model_id" in content
    assert "version" in content
    assert "manifest" in content
    assert "content" in content