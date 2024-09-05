from flask import Blueprint, request, send_from_directory, Response
import os
import uuid
import logging
from flask import current_app

bp = Blueprint('api', __name__)

MODEL_FOLDER = './models'
ONE_GB_IN_BYTES = 1024 ** 3

@bp.route('/upload', methods=['POST'])
def upload():
    try:
        current_app.logger.info("Upload request received")
        
        if 'file' not in request.files:
            current_app.logger.error("No file part in the request")
            return Response('No file part', status=400)
        
        file = request.files['file']

        if file.filename == '':
            current_app.logger.error("No selected file")
            return Response('No selected file', status=400)

        if file.content_length > ONE_GB_IN_BYTES:
            current_app.logger.error("File size exceeds the limit")
            return Response('File size exceeds the limit', status=413)
        
        if not os.path.exists(MODEL_FOLDER):
            os.makedirs(MODEL_FOLDER)
            current_app.logger.info(f"Created MODEL_FOLDER: {MODEL_FOLDER}")

        temp_file_name = str(uuid.uuid4())
        temp_file_path = os.path.join(MODEL_FOLDER, temp_file_name)
        file.save(temp_file_path)
        current_app.logger.info(f"Saved model to temp file: {temp_file_name}")

        file_cid = temp_file_name  # Use the temp file name as the CID for simplicity
        os.rename(temp_file_path, os.path.join(MODEL_FOLDER, file_cid))

        current_app.logger.info(f"Saved model locally with CID: {file_cid}")
        return file_cid
    except Exception as e:
        current_app.logger.error(f"Error in upload: {str(e)}")
        return Response(f"Internal Server Error: {str(e)}", status=500)

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
