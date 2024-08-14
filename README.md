# vanna-storage

Decentralized Private IPFS Filestore for Vanna Blockchain

Consists of 2 services:

- `vanna-storage`: storage node exposing model storage APIs on top of IPFS
- `ipfs`: IPFS node configured with private swarm

## How to run 

We use Docker and docker-compose to run these services.

First, to build the `vanna-storage` docker image, run `make docker`.

Once this is done, run `make run` to start up the 2 docker containers.
If you only want to start/restart a single service, use `docker-compose up ipfs` or `docker-compose up vanna-storage`.

To run a server locally, outside of docker, you need to install `virtualenv` and install dependencies from the `requirements.txt` file, then run `python3 src/app.py`.

#### Alternatively, you can use docker directly:
- To restart the server when developing:
```
docker compose build --no-cache server && docker compose up -d server && docker compose logs -f server
```

- To restart both ipfs and the server:
```
docker compose down && docker compose build --no-cache server && docker compose up -d && docker compose logs -f server
```

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
curl -X POST -H "Content-Type: multipart/form-data" \
     -F "file=@tests/mock_onnx/test_model.onnx" \
     -F "model_id=test_identity_model" \
     http://localhost:5002/upload_model
```
```
{"manifest_cid":"Qmd5fxJ9CCjypBthgeN2chFgYrWS2EzBegfFytsT5s5pNG","version":"1.07"}
```

2. Download a model:
```
curl -OJ http://localhost:5002/download_model/multi_file_model/1.00 
```

```
  % Total    % Received % Xferd  Average Speed   Time    Time     Time  Current
                                 Dload  Upload   Total   Spent    Left  Speed
100    98  100    98    0     0   3527      0 --:--:-- --:--:-- --:--:--  3629
```

- model metadata with a single file will download the file directly, multiple files will be downloaded as a zip file

3. Download the model using query parameters:
```                                                                                                       
curl -X GET "http://localhost:5002/download_model?model_id=test_identity_model&version=1.00" \
     --output downloaded_test_model_query.onnx
```
```
  % Total    % Received % Xferd  Average Speed   Time    Time     Time  Current
                                 Dload  Upload   Total   Spent    Left  Speed
100    98  100    98    0     0   5802      0 --:--:-- --:--:-- --:--:--  6125
```

4. Get model info
```
curl -X GET http://localhost:5002/model_info/test_identity_model/1.07
```
```
{"created_at":"2024-08-05T19:17:19.031251","model_file_cid":"QmcLNqhhS8w5mapFr593Qx6DKj2itt3FPXL4kqPTAuWhcx","model_file_name":"test_model.onnx","model_file_type":"onnx","model_id":"test_identity_model","version":"1.07"}
```

5. Get latest model info:
```
curl -X GET http://localhost:5002/model_info/test_identity_model
```
```
{"created_at":"2024-08-05T19:17:19.031251","model_file_cid":"QmcLNqhhS8w5mapFr593Qx6DKj2itt3FPXL4kqPTAuWhcx","model_file_name":"test_model.onnx","model_file_type":"onnx","model_id":"test_identity_model","version":"1.07"}
```

6. List versions of a model:
```
curl -X GET http://localhost:5002/list_versions/test_identity_model
```
```
{"model_id":"test_identity_model","versions":["1.00","1.01","1.02","1.03","1.04","1.05","1.06","1.07"]}
```


7. Get all latest models:
```
curl -X GET http://localhost:5002/all_latest_models
```
```
{"test_identity_model":{"cid":"Qmd5fxJ9CCjypBthgeN2chFgYrWS2EzBegfFytsT5s5pNG","version":"1.07"},"test_onnx_model_1722462268":{"cid":"QmTRdxNTyae8Rkdhxh4tzMd34ocPLigmQf8dTx26Fe9RgR","version":"1.00"}}
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
