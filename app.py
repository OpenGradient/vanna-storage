from flask import Flask, request
from ipfshttpclient import connect
import subprocess

app = Flask(__name__)

UPLOAD_FOLDER = './uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

@app.route('/upload', methods=['POST'])

def uploadFile():
    if 'file' not in request.files:
        return 'No file part'

    file = request.files['file']

    # If the user does not select a file, the browser submits an empty file without a filename
    if file.filename == '':
        return 'No selected file'

    # Save the file and upload it to IPFS
    file_path = f"{app.config['UPLOAD_FOLDER']}/{file.filename}"
    file.save(file_path)
    cid = subprocess.getoutput("ipfs add " + file_path)

    return f'File uploaded to IPFS with hash: {cid}'

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')

