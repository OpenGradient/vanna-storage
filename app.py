from flask import Flask, request, send_file
import subprocess
import os

app = Flask(__name__)

MODEL_FOLDER = './models'
app.config['MODEL_FOLDER'] = MODEL_FOLDER 

@app.route('/upload', methods=['POST'])
def upload():
    if 'file' not in request.files:
        return 'No file part'

    file = request.files['file']

    # If the user does not select a file, the browser submits an empty file without a filename
    if file.filename == '':
        return 'No selected file'

    # Save the file and upload it to IPFS
    file_path = f"{app.config['MODEL_FOLDER']}/{file.filename}"
    file.save(file_path)
    cid = subprocess.getoutput("ipfs add " + file_path).split("added ")[1].split(" ")[0]

    return f'File uploaded to IPFS with hash: {cid}'

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
