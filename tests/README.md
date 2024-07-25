# Model Repository Test Suite

This README provides an overview of the test suite for the Model Repository project.

## Overview

The test suite consists of two main files:
- `test_model_repository.py`: Unit tests for the ModelRepository class
- `test_api_integration.py`: Integration tests for the API endpoints

## Running the Tests

To run the tests, use the following commands:
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

## Troubleshooting

If tests are failing:
1. Check if the API server is running for integration tests.
2. Verify that mock data is present and correctly located.
3. Ensure all dependencies are installed and up to date.
4. Check for any changes in the main codebase that might affect the tests.