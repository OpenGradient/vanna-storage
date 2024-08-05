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
IPFS_URL = "http://localhost:5001/api/v0"

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
            data = {"model_id": model_id}
            response = client.post("/upload_model", files=files, data=data)

        assert response.status_code == 200
        response_json = response.json()
        assert "manifest_cid" in response_json
        assert "version" in response_json

        # Check the model info
        model_info_response = client.get(f"/model_info/{model_id}/{response_json['version']}")
        assert model_info_response.status_code == 200
        model_info = model_info_response.json()
        assert model_info["model_id"] == model_id
        assert model_info["version"] == response_json["version"]
        assert "model_file_cid" in model_info

    def test_list_versions(self, client):
        model_id = f"test_onnx_model_{int(time.time())}"
        versions = []

        # Check initial state
        initial_list_response = client.get(f"/list_versions/{model_id}")
        initial_versions = initial_list_response.json().get("versions", [])
        print(f"Initial versions: {initial_versions}")

        # Upload multiple versions
        for i in range(3):
            with open("tests/mock_onnx/test_model.onnx", "rb") as f:
                files = {"file": ("test_model.onnx", f)}
                data = {"model_id": model_id}
                response = client.post("/upload_model", files=files, data=data)
            assert response.status_code == 200
            version = response.json()["version"]
            versions.append(version)
            print(f"Uploaded version: {version}")

            # Check versions after each upload
            interim_list_response = client.get(f"/list_versions/{model_id}")
            print(f"Versions after upload {i+1}: {interim_list_response.json()}")

        # List versions
        list_response = client.get(f"/list_versions/{model_id}")
        assert list_response.status_code == 200
        listed_versions = list_response.json()["versions"]
        print(f"Versions from upload: {versions}")
        print(f"Final listed versions: {listed_versions}")

        # Check if all uploaded versions are in the final list
        assert set(versions).issubset(set(listed_versions))
        # Check if there's at most one additional version (the initial 1.00)
        assert len(listed_versions) <= len(versions) + 1

    def test_download_model(self, client):
        model_id = f"test_onnx_model_{int(time.time())}"
        with open("tests/mock_onnx/test_model.onnx", "rb") as f:
            original_data = f.read()
            files = {"file": ("test_model.onnx", f)}
            data = {"model_id": model_id}
            response = client.post("/upload_model", files=files, data=data)

        assert response.status_code == 200
        version = response.json()["version"]

        # Download the model
        download_response = client.get(f"/download_model/{model_id}/{version}")
        assert download_response.status_code == 200
        assert download_response.content == original_data

    def test_get_all_latest_models(self, client):
        model_ids = [f"test_onnx_model_{i}_{int(time.time())}" for i in range(3)]

        for model_id in model_ids:
            with open("tests/mock_onnx/test_model.onnx", "rb") as f:
                files = {"file": ("test_model.onnx", f)}
                data = {"model_id": model_id}
                response = client.post("/upload_model", files=files, data=data)
            assert response.status_code == 200

        # Get all latest models
        latest_models_response = client.get("/all_latest_models")
        assert latest_models_response.status_code == 200
        latest_models = latest_models_response.json()

        for model_id in model_ids:
            assert model_id in latest_models
            assert "version" in latest_models[model_id]
            assert "cid" in latest_models[model_id]