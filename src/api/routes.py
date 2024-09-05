from flask import Blueprint, request, send_from_directory, Response
import os
import uuid
import logging

bp = Blueprint('api', __name__)

MODEL_FOLDER = './models'
ONE_GB_IN_BYTES = 1024 ** 3

@bp.route('/upload', methods=['POST'])
def upload():
    if 'file' not in request.files:
        return Response('No file part', status=400)
    file = request.files['file']

    if file.filename == '':
        return Response('No selected file', status=400)

    if file.content_length > ONE_GB_IN_BYTES:
        return Response('File size exceeds the limit', status=413)
    
    temp_file_name = str(uuid.uuid4())
    temp_file_path = os.path.join(MODEL_FOLDER, temp_file_name)
    file.save(temp_file_path)
    logging.info(f"Saved model to temp file: {temp_file_name}")

    file_cid = temp_file_name  # Use the temp file name as the CID for simplicity
    os.rename(temp_file_path, os.path.join(MODEL_FOLDER, file_cid))

    logging.info(f"Saved model locally with CID: {file_cid}")
    return file_cid

@bp.route('/download', methods=['GET'])
def download():
    file_cid = request.args.get('cid')

    if not file_cid:
        return Response('Empty CID', 400)

    if os.path.basename(file_cid) != file_cid:
        return Response('Invalid CID', 400)

    file_path = os.path.abspath(os.path.join(MODEL_FOLDER, file_cid))

    if os.path.exists(file_path):
        return send_from_directory(MODEL_FOLDER, file_cid, as_attachment=True)
    else:
        return Response("File not found", status=404)
