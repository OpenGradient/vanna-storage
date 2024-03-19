sudo apt-get update
sudo apt-get install golang-go -y
wget https://dist.ipfs.io/go-ipfs/v0.27.0/go-ipfs_v0.27.0_linux-386.tar.gz
tar xvfz go-ipfs_v0.27.0_linux-386.tar.gz
sudo mv go-ipfs/ipfs /usr/local/bin/ipfs
ipfs --version
