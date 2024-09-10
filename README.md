# vanna-storage

Simple Flask application for uploading and downloading models to and from IPFS.

## How to run 

We use Docker and docker-compose to run these services.

First, to build the `vanna-storage` docker image, run `make docker`.

Once this is done, run `make run` to start up the docker container.

To run a server locally, outside of docker, you need to install `virtualenv` and install dependencies from the `requirements.txt` file, then run `python3 src/app.py`.

## API Endpoints

### Upload a model
#### POST /upload
- **Parameters:**
  - `file`: The file to upload (multipart/form-data)
  - `stream` (optional): Set to `true` to enable streaming upload

- **Example:**
  ```bash
  curl -X POST -H "Content-Type: multipart/form-data" -F "file=@model.onnx" "http://localhost:5002/upload?stream=true"
  ```

- **Response:**
  ```json
  {
    "cid":"QmWtrojv4a43gfRtthsHerAc8USRuxkxhNrVCS6b3FA23F","size":412,"upload_time":0.027422666549682617
  }
  ```

### Download a model
#### GET /download
- **Parameters:**
  - `cid`: The CID of the file to download
  - `stream` (optional): Set to `true` to enable streaming download

- **Example:**
  ```bash
  curl -X GET "http://localhost:5002/download?cid=QmHash...&stream=true" --output downloaded_file
  ```

### Get file size
#### GET /get_file_size
- **Parameters:**
  - `cid`: The CID of the file

- **Example:**
  ```bash
  curl -X GET "http://localhost:5002/get_file_size?cid=QmHash..."
  ```

- **Response:**
  ```json
  {
    "cid": "QmHash...",
    "size": 1024
  }
  ```
