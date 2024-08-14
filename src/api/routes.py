from flask import Blueprint, request, jsonify, Response, current_app
from core.model_repository import ModelRepository
from core.ipfs_client import IPFSClient
from packaging import version as parse
import json
import io
import zipfile
import logging

bp = Blueprint('api', __name__)

class InvalidUsage(Exception):
    status_code = 400

    def __init__(self, message, status_code=None, payload=None):
        super().__init__()
        self.message = message
        if status_code is not None:
            self.status_code = status_code
        self.payload = payload

    def to_dict(self):
        rv = dict(self.payload or ())
        rv['message'] = self.message
        rv['error'] = str(self.__cause__) if self.__cause__ else None
        return rv

@bp.errorhandler(InvalidUsage)
def handle_invalid_usage(error):
    response = jsonify(error.to_dict())
    response.status_code = error.status_code
    return response

@bp.errorhandler(404)
def not_found(error):
    return jsonify({"error": str(error), "message": "Not found"}), 404

@bp.errorhandler(500)
def internal_error(error):
    return jsonify({"error": str(error), "message": "Internal server error"}), 500

model_repo = ModelRepository()

@bp.route('/upload_model', methods=['POST'])
def route_upload_model():
    model_id = request.form.get('model_id')
    metadata = request.form.get('metadata', '{}')
    
    if not model_id:
        logging.error("Missing model_id")
        raise InvalidUsage('Missing model_id', status_code=400)
    
    files = request.files
    if not files:
        logging.error("No files uploaded")
        raise InvalidUsage('No files uploaded', status_code=400)
    
    try:
        metadata_dict = json.loads(metadata)
        file_dict = {file.filename: file for file in files.getlist('files')}
        manifest_cid, new_version = model_repo.upload_model(model_id, file_dict, metadata_dict)
        return jsonify({'manifest_cid': manifest_cid, 'version': new_version})
    except json.JSONDecodeError:
        logging.error("Invalid JSON in metadata")
        raise InvalidUsage('Invalid JSON in metadata', status_code=400)
    except Exception as e:
        logging.error(f"Error uploading model: {str(e)}")
        raise InvalidUsage('Error uploading model', status_code=500, payload={'details': str(e)})

@bp.route('/download_model', methods=['GET'])
@bp.route('/download_model/<model_id>/<version>', methods=['GET'])
def route_download_model(model_id=None, version=None):
    if model_id is None:
        model_id = request.args.get('model_id')
    if version is None:
        version = request.args.get('version')
    
    if not model_id or not version:
        raise InvalidUsage('Missing model_id or version', status_code=400)
    
    try:
        model_files = model_repo.download_model(model_id, version)
        if len(model_files) == 1:
            file_name, file_content = next(iter(model_files.items()))
            return Response(file_content, mimetype='application/octet-stream',
                            headers={'Content-Disposition': f'attachment;filename={version}.{model_id}.{file_name}'})
        else:
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                for file_name, file_content in model_files.items():
                    zip_file.writestr(file_name, file_content)
            zip_buffer.seek(0)
            return Response(zip_buffer.getvalue(), mimetype='application/zip',
                            headers={'Content-Disposition': f'attachment;filename={version}.{model_id}.zip'})
    except Exception as e:
        current_app.logger.error(f"Error downloading model: {str(e)}")
        raise InvalidUsage('Error downloading model', status_code=500, payload={'details': str(e)})

@bp.route('/list_versions/<model_id>', methods=['GET'])
def route_list_versions(model_id):
    try:
        versions = model_repo.list_versions(model_id)
        sorted_versions = sorted(versions, key=lambda v: parse.parse(v))
        return jsonify({'model_id': model_id, 'versions': sorted_versions})
    except Exception as e:
        current_app.logger.error(f"Error listing versions: {str(e)}")
        raise InvalidUsage('Error listing versions', status_code=500, payload={'details': str(e)})

@bp.route('/latest_version/<model_id>', methods=['GET'])
def route_get_latest_version(model_id):
    try:
        latest_version = model_repo.get_latest_version(model_id)
        return jsonify({'model_id': model_id, 'latest_version': latest_version})
    except Exception as e:
        current_app.logger.error(f"Error getting latest version: {str(e)}")
        raise InvalidUsage('Error getting latest version', status_code=500, payload={'details': str(e)})

@bp.route('/all_latest_models', methods=['GET'])
def route_get_all_latest_models():
    try:
        latest_models = model_repo.get_all_latest_models()
        return jsonify(latest_models)
    except Exception as e:
        current_app.logger.error(f"Error getting all latest models: {str(e)}")
        raise InvalidUsage('Error getting all latest models', status_code=500, payload={'details': str(e)})
    
@bp.route('/all_objects', methods=['GET'])
def route_get_all_objects():
    try:
        all_objects = model_repo.get_all_objects()
        return jsonify(all_objects)
    except Exception as e:
        current_app.logger.error(f"Error getting all objects: {str(e)}")
        raise InvalidUsage('Error getting all objects', status_code=500, payload={'details': str(e)})

@bp.route('/model_info/<model_id>', methods=['GET'])
@bp.route('/model_info/<model_id>/<version>', methods=['GET'])
def route_get_model_info(model_id, version=None):
    try:
        if version is None:
            version = model_repo.get_latest_version(model_id)
        model_info = model_repo.get_model_info(model_id, version)
        return jsonify(model_info)
    except Exception as e:
        current_app.logger.error(f"Error getting model info: {str(e)}")
        raise InvalidUsage('Error getting model info', status_code=500, payload={'details': str(e)})

@bp.route('/update_model_metadata/<model_id>/<version>', methods=['PUT'])
def route_update_model_metadata(model_id, version):
    try:
        new_metadata = request.json
        updated_info = model_repo.update_model_metadata(model_id, version, new_metadata)
        return jsonify(updated_info['metadata'])
    except ValueError as ve:
        error_message = str(ve)
        logging.error(f"ValueError: {error_message}")
        return jsonify({"error": "Invalid manifest", "message": error_message}), 400
    except KeyError as ke:
        error_message = f"Missing key in manifest: {str(ke)}"
        logging.error(error_message)
        return jsonify({"error": "Invalid manifest structure", "message": error_message}), 400
    except Exception as e:
        logging.error(f"Unexpected error updating model metadata: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": "Internal server error", "message": str(e)}), 500