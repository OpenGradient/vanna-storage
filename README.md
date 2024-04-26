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