from flask import Flask, request, send_file, Response
import subprocess
import os
import uuid

app = Flask(__name__)

MODEL_FOLDER = './models'
app.config['MODEL_FOLDER'] = MODEL_FOLDER 

@app.route('/upload', methods=['POST'])
def upload():
    if 'file' not in request.files:
        return Response('No file part', status=400)

    file = request.files['file']

    # If the user does not select a file, the browser submits an empty file without a filename
    if file.filename == '':
        return Response('No selected file', status=400)

    # Save the file to local disk first
    unique_file_name = f"{file.filename}-{uuid.uuid4()}"
    file_path = f"{app.config['MODEL_FOLDER']}/{unique_file_name}"
    file.save(file_path)

    # upload to IPFS
    cid = subprocess.getoutput("ipfs add " + file_path).split("added ")[1].split(" ")[0]

    return cid

@app.route('/download', methods=['GET'])
def download():
    filename = request.args.get('cid')
    filepath = MODEL_FOLDER + "/" + filename
    # Check if the file exists
    if not os.path.exists(filepath):
        retrieveFile(filename)
    if os.path.exists(filepath):
        # Return the file as a response
        return send_file(filepath, as_attachment=True)
    else:
        return "File not found", 404

def retrieveFile(filename):
    os.system("ipfs get " + filename + " -o " + MODEL_FOLDER + "/" + filename)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
