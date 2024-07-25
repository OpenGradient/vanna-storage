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

Alternatively, you can use docker directly:
- To restart the server when developing:
```
docker compose build --no-cache server && docker compose up -d server && docker compose logs -f server
```

- To restart both ipfs and the server:
```
docker compose down && docker compose build --no-cache server && docker compose up -d && docker compose logs -f server
```
- When running test_model_repository from local, be sure to run 
```
   export IPFS_HOST=localhost
```

## Test Commands
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
