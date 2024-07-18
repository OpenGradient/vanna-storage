from flask import Blueprint, request, Response, send_from_directory, jsonify
from utils import validate_file
import logging
import os
from config import MODEL_FOLDER
from model_repository import ModelRepository

bp = Blueprint('routes', __name__)
model_repo = ModelRepository()

@bp.route('/upload_model', methods=['POST'])
def upload_model():
    file = request.files.get('file')
    model_id = request.form.get('model_id')
    version = request.form.get('version')
    if not file or not model_id or not version:
        return Response('Missing file, model_id, or version', status=400)

    validation_response = validate_file(file)
    if validation_response:
        return validation_response

    try:
        serialized_model = file.read()
        manifest_cid = model_repo.upload_model(model_id, serialized_model, version)
        logging.info(f"Uploaded model {model_id} version {version} to IPFS: {manifest_cid}")
        return jsonify({'manifest_cid': manifest_cid})
    except Exception as e:
        logging.error(f"Failed to upload model: {e}")
        return Response("Failed to upload model", status=500)

@bp.route('/add_model', methods=['POST'])
def add_model():
    file = request.files.get('file')
    model_id = request.form.get('model_id')
    new_version = request.form.get('new_version')
    if not file or not model_id or not new_version:
        return Response('Missing file, model_id, or new_version', status=400)

    validation_response = validate_file(file)
    if validation_response:
        return validation_response

    try:
        serialized_model = file.read()
        manifest_cid = model_repo.add_model(model_id, serialized_model, new_version)
        logging.info(f"Added new version {new_version} of model {model_id} to IPFS: {manifest_cid}")
        return jsonify({'manifest_cid': manifest_cid})
    except Exception as e:
        logging.error(f"Failed to add new model version: {e}")
        return Response("Failed to add new model version", status=500)

@bp.route('/download_model', methods=['GET'])
def download_model():
    model_id = request.args.get('model_id')
    version = request.args.get('version')
    if not model_id or not version:
        return Response('Missing model_id or version', status=400)

    try:
        model_data = model_repo.download_model(model_id, version)
        return Response(model_data, mimetype='application/octet-stream')
    except Exception as e:
        logging.error(f"Failed to download model: {e}")
        return Response("Failed to download model", status=500)

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

@bp.route('/rollback_version', methods=['POST'])
def rollback_version():
    data = request.json
    model_id = data.get('model_id')
    version = data.get('version')
    if not model_id or not version:
        return jsonify({'error': 'Missing model_id or version'}), 400
    success = model_repo.rollback_version(model_id, version)
    return jsonify({'success': success})
