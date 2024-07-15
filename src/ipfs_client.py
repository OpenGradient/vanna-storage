import ipfshttpclient

def ipfs_client():
    # connect to local IPFS daemon
    return ipfshttpclient.connect('/ip4/127.0.0.1/tcp/5001/http')
