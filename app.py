from flask import Flask, request
from ipfshttpclient import connect

app = Flask(__name__)

@app.route('/upload', methods=['POST'])
def uploadFile():
    if 'file' not in request.files:
        return 'No file part'

    file = request.files['file']

    # If the user does not select a file, the browser submits an empty file without a filename
    if file.filename == '':
        return 'No selected file'

    # Else, upload the file to IPFS
    ipfs_client = connect('/ip4/3.140.191.156/tcp/4001/p2p/12D3KooWQWntZ1RYAxBtqbPcRz1e24o9xzXkvieJnhhNAC6xKwAF')

    # Upload the file to IPFS
    ipfs_response = ipfs_client.add_bytes(file.read())

    # Get the IPFS hash of the uploaded file
    ipfs_hash = ipfs_response['Hash']

    return f'File uploaded to IPFS with hash: {ipfs_hash}' 

if __name__ == '__main__':
    app.run(debug=True)

