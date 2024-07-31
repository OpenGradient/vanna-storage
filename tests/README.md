# Model Repository Test Suite

This README provides an overview of the test suite for the Model Repository project.

## Overview

The test suite consists of two main files:
- `test_model_repository.py`: Unit tests for the ModelRepository class
- `test_api_integration.py`: Integration tests for the API endpoints

## Setup & Running the Tests

- When running test_model_repository from local, be sure to run:
```
export IPFS_HOST=localhost
```

- To run the tests, use the following commands:
```
pytest tests/test_model_repository.py -v -s
pytest tests/test_api_integration.py -v -s
```


## Test Structure

### Unit Tests (test_model_repository.py)
This file contains unit tests for various methods of the ModelRepository class, including:
- Downloading models
- Getting the latest version
- Listing versions
- Uploading models
- Validating versions

### Integration Tests (test_api_integration.py)

This file contains integration tests that interact with the API endpoints, including:
- Uploading models
- Listing versions
- Listing content

## Mock Data

The tests use mock ONNX models located in the `tests/mock_onnx/` directory.

## Test Setup

The unit tests use `unittest.mock` to mock the IPFS client and other dependencies. The integration tests use `httpx` to make HTTP requests to the API.

## Adding New Tests

When adding new tests:
1. For unit tests, add them to the `TestModelRepository` class in `test_model_repository.py`.
2. For integration tests, add new functions prefixed with `test_` in `test_api_integration.py`.

## Manual Test Commands

To test the ModelRepository functionality, you can use the following curl commands:

1. Upload the mock ONNX model:
```
❯ curl -X POST -H "Content-Type: multipart/form-data" \
     -F "file=@tests/mock_onnx/test_model.onnx" \
     -F "model_id=test_identity_model" \
     http://localhost:5002/upload_model
{"manifest_cid":"QmSKJWWMwdZ1dvYUo9nhv3jATAiNtdsqyWpyQHqHL4RdGg","version":"1.00"}
```

2. Get model metadata:
```
❯ curl -X GET http://localhost:5002/model_metadata/test_identity_model
{"latest_version":"1.00","versions":{"1.00":"QmSKJWWMwdZ1dvYUo9nhv3jATAiNtdsqyWpyQHqHL4RdGg"}}
```

3. Get model info (assuming the server assigned version 1.00)
```
❯ curl -X GET http://localhost:5002/model_info/test_identity_model/1.00
{"manifest_content":{"created_at":"2024-07-31T21:35:03.266643","model_cid":"QmcLNqhhS8w5mapFr593Qx6DKj2itt3FPXL4kqPTAuWhcx","model_id":"test_identity_model","version":"1.00"},"metadata_manifest_cid":"QmSKJWWMwdZ1dvYUo9nhv3jATAiNtdsqyWpyQHqHL4RdGg","model_content":{"content":{"model":"QmcLNqhhS8w5mapFr593Qx6DKj2itt3FPXL4kqPTAuWhcx"},"manifest":{"created_at":"2024-07-31T21:35:03.266643","model_cid":"QmcLNqhhS8w5mapFr593Qx6DKj2itt3FPXL4kqPTAuWhcx","model_id":"test_identity_model","version":"1.00"}}}
```

4. Download the model using query parameters:
```                                                                                                       
❯ curl -X GET "http://localhost:5002/download_model?model_id=test_identity_model&version=1.00" \
     --output downloaded_test_model_query.onnx
  % Total    % Received % Xferd  Average Speed   Time    Time     Time  Current
                                 Dload  Upload   Total   Spent    Left  Speed
100    98  100    98    0     0   5802      0 --:--:-- --:--:-- --:--:--  6125
```

5. Download the model using path parameters:
```
❯ curl -X GET http://localhost:5002/download_model/test_identity_model/1.00 \
     --output downloaded_test_model_path.onnx
  % Total    % Received % Xferd  Average Speed   Time    Time     Time  Current
                                 Dload  Upload   Total   Spent    Left  Speed
100    98  100    98    0     0   4430      0 --:--:-- --:--:-- --:--:--  4454
```

6. Get the entire model repository metadata:
```
❯ curl -X GET http://localhost:5002/model_repo_metadata
{"models":{"test_identity_model":{"latest_version":"1.00","versions":{"1.00":"QmSKJWWMwdZ1dvYUo9nhv3jATAiNtdsqyWpyQHqHL4RdGg"}}},"version":"1.0"}
```

7. Get model info for a non-existent model (should return an error):
```
❯ curl -X GET http://localhost:5002/model_info/non_existent_model/1.00
{"error":null,"message":"No manifest found for non_existent_model version 1.00"}
```

8. Upload a new version of the model:
```
❯ curl -X POST -H "Content-Type: multipart/form-data" \
     -F "file=@tests/mock_onnx/test_model.onnx" \
     -F "model_id=test_identity_model" \
     http://localhost:5002/upload_model
{"manifest_cid":"QmSMcB7ArKRdUfqaU9kznJrBuhZ9pr3Hd6QKqyqcHRZHry","version":"1.01"}
```

9. Validate new version exists:
```
❯ curl -X GET http://localhost:5002/model_repo_metadata               
{"models":{"test_identity_model":{"latest_version":"1.01","versions":{"1.00":"QmSKJWWMwdZ1dvYUo9nhv3jATAiNtdsqyWpyQHqHL4RdGg","1.01":"QmSMcB7ArKRdUfqaU9kznJrBuhZ9pr3Hd6QKqyqcHRZHry"}}},"version":"1.0"}
```

10. List all versions of a model:
```
❯ curl -X GET http://localhost:5002/list_versions/test_identity_model
{"model_id":"test_identity_model","versions":["1.00","1.01"]}
```

These commands cover the main functionalities of the ModelRepository. Make sure to run them in the order presented, as some commands depend on the results of previous ones.

## Troubleshooting

If tests are failing:
1. Check if the API server is running for integration tests.
2. Verify that mock data is present and correctly located.
3. Ensure all dependencies are installed and up to date.
4. Check for any changes in the main codebase that might affect the tests.
5. Verify that the IPFS daemon is running and accessible.
6. Check the API server logs for any error messages or unexpected behavior.