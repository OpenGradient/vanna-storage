# vanna-storage

Simple Flask application for uploading and downloading models to and from IPFS.

## How to run 

We use Docker and docker-compose to run these services.

First, to build the `vanna-storage` docker image, run `make docker`.

Once this is done, run `make run` to start up the docker container.

To run a server locally, outside of docker, you need to install `virtualenv` and install dependencies from the `requirements.txt` file, then run `python3 src/app.py`.

## API Endpoints

### Upload a model
