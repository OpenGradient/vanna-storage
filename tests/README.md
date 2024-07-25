# Model Repository Test Suite

This README provides an overview of the test suite for the Model Repository project.

## Overview

The test suite consists of two main files:
- `test_model_repository.py`: Unit tests for the ModelRepository class
- `test_api_integration.py`: Integration tests for the API endpoints

## Setup & Running the Tests
- When running test_model_repository from local, be sure to run 
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

1. Upload a new model:  
```
curl -X POST \
-F "file=@test/mock_onnx/test_model.onnx" \
-F "model_id=test_onnx_model" \
-F "version=1.0" \
http://localhost:5002/upload_model
```

2. Add a new version of an existing model:  
```
curl -X POST \
-F "file=@test/mock_onnx/test_model.onnx" \
-F "model_id=test_onnx_model" \
-F "new_version=1.1" \
http://localhost:5002/add_model
```

3. Download a specific version of a model:
```
curl -X GET \
"http://localhost:5002/download_model?model_id=test_onnx_model&version=1.0" \
--output downloaded_model.onnx
```

4. Validate a new version:
```
curl -X POST \
-H "Content-Type: application/json" \
-d '{"model_id": "test_onnx_model", "new_version": "1.2"}' \
http://localhost:5002/validate_version
```

5. List versions of a model:
```
curl -X GET \
http://localhost:5002/list_versions/test_onnx_model
```

6. Get the latest version of a model:
```
curl -X GET \
http://localhost:5002/get_latest_version/test_onnx_model
```

7. Rollback to a previous version:
```
curl -X POST \
-H "Content-Type: application/json" \
-d '{"model_id": "test_onnx_model", "version": "1.0"}' \
http://localhost:5002/rollback_version
```

These commands cover the main functionalities of the ModelRepository. Make sure to run them in the order presented, as some commands depend on the results of previous ones.


## Troubleshooting

If tests are failing:
1. Check if the API server is running for integration tests.
2. Verify that mock data is present and correctly located.
3. Ensure all dependencies are installed and up to date.
4. Check for any changes in the main codebase that might affect the tests.