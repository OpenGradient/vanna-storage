from flask import Blueprint, request, Response, send_from_directory, jsonify
from utils import validate_file
import logging
import os
from config import MODEL_FOLDER
from model_repository import ModelRepository  # Assuming this is the class handling IPFS operations

bp = Blueprint('routes', __name__)
model_repo = ModelRepository()

@bp.route('/validate_version', methods=['POST'])
def validate_version():
    data = request.json
    model_id = data.get('model_id')
    new_version = data.get('new_version')
    if not model_id or not new_version:
        return jsonify({'error': 'Missing model_id or new_version'}), 400
    is_valid = model_repo.validate_version(model_id, new_version)
    return jsonify({'is_valid': is_valid})

@bp.route('/list_versions/<model_id>', methods=['GET'])
def list_versions(model_id):
    versions = model_repo.list_versions(model_id)
    if versions:
        return jsonify({'versions': versions})
    else:
        return jsonify({'error': f'No versions found for model_id {model_id}'}), 404

@bp.route('/get_latest_version/<model_id>', methods=['GET'])
def get_latest_version(model_id):
    try:
        latest_version = model_repo.get_latest_version(model_id)
        return jsonify({'latest_version': latest_version})
    except ValueError as e:
        return jsonify({'error': str(e)}), 404

@bp.route('/upload', methods=['POST'])
def upload():
    file = request.files.get('file')
    if not file:
        return Response('No file part', status=400)

    validation_response = validate_file(file)
    if validation_response:
        return validation_response

    try:
        file_cid = model_repo.upload(file)
        logging.info(f"Uploaded model to IPFS: {file_cid}")
        return file_cid
    except Exception as e:
        logging.error(f"Failed to upload model: {e}")
        return Response("Failed to upload file", status=500)

@bp.route('/download', methods=['GET'])
def download():
    file_cid = request.args.get('cid')

    if not file_cid:
        return Response('Empty CID', 400)

    # Prevent directory traversal attack
    if os.path.basename(file_cid) != file_cid:
        return Response('Invalid CID', 400)

    try:
        file_path = model_repo.download(file_cid, MODEL_FOLDER)
        if file_path:
            return send_from_directory(MODEL_FOLDER, os.path.basename(file_path), as_attachment=True)
        else:
            return Response("File not found", status=404)
    except Exception as e:
        logging.error(f"Failed to download model: {e}")
        return Response("Failed to download file", status=500)