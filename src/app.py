from flask import Flask, request, send_from_directory, Response
import ipfshttpclient
import os
import uuid
import logging

app = Flask(__name__)

MODEL_FOLDER = './models'
ONE_GB_IN_BYTES = 1024 ** 3


@app.route('/upload', methods=['POST'])
def upload():
    if 'file' not in request.files:
        return Response('No file part', status=400)
    file = request.files['file']

    # If the user does not select a file, the browser submits an empty file without a filename
    if file.filename == '':
        return Response('No selected file', status=400)

    if file.content_length > ONE_GB_IN_BYTES:
        return Response('File size exceeds the limit', status=413)
    
    # Save the file to local disk first
    temp_file_name = str(uuid.uuid4())
    temp_file_path = os.path.join(MODEL_FOLDER, temp_file_name)
    file.save(temp_file_path)
    logging.info(f"Saved model to temp file: {temp_file_name}")

    with ipfs_client() as client:
        upload_result = client.add(temp_file_path)
        file_cid = upload_result['Hash']
        
        # rename to CID filename
        os.rename(temp_file_path, os.path.join(MODEL_FOLDER, file_cid))

        logging.info(f"Uploaded model to IPFS: {file_cid}, temp_file_name: {temp_file_name}")
        return file_cid

@app.route('/download', methods=['GET'])
def download():
    file_cid = request.args.get('cid')

    # check input for traversal attack
    if os.path.basename(file_cid) != file_cid:
        return Response('Invalid CID', 400)

    file_path = os.path.abspath(os.path.join(MODEL_FOLDER, file_cid))

    # Download file if not stored locally
    if not os.path.exists(file_path):
        with ipfs_client() as client:
            client.get(file_cid, target=file_path)

    if os.path.exists(file_path):
        # Return the file as a response
        return send_from_directory(MODEL_FOLDER, file_cid, as_attachment=True)
    else:
        return Response("File not found", status=404)

def ipfs_client():
    # connect to local IPFS daemon
    return ipfshttpclient.connect('/ip4/127.0.0.1/tcp/5001/http')

if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        filename='app.log',
        filemode='w')

    app.run(debug=True, host='0.0.0.0')
