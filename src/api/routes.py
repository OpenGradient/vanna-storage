from flask import Blueprint, request, jsonify, Response, current_app
from core.model_repository import ModelRepository
from core.ipfs_client import IPFSClient
from packaging import version as parse
from core.model_metadata import ModelMetadata
import json

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
    current_app.logger.info("Received upload_model request")
    file = request.files.get('file')
    model_id = request.form.get('model_id')
    metadata = request.form.get('metadata', '{}')
    
    if not file or not model_id:
        current_app.logger.error("Missing file or model_id")
        raise InvalidUsage('Missing file or model_id', status_code=400)
    
    try:
        metadata_dict = json.loads(metadata)
        current_app.logger.info(f"Uploading model with ID: {model_id}")
        manifest_cid, new_version = model_repo.upload_model(model_id, file, metadata_dict)
        current_app.logger.info(f"Model uploaded successfully. CID: {manifest_cid}, Version: {new_version}")
        return jsonify({'manifest_cid': manifest_cid, 'version': new_version})
    except json.JSONDecodeError:
        current_app.logger.error("Invalid JSON in metadata")
        raise InvalidUsage('Invalid JSON in metadata', status_code=400)
    except Exception as e:
        current_app.logger.error(f"Error uploading model: {str(e)}", exc_info=True)
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
        model_data = model_repo.download_model(model_id, version)
        return Response(model_data, mimetype='application/octet-stream',
                        headers={'Content-Disposition': f'attachment;filename={model_id}_{version}.onnx'})
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

@bp.route('/model_metadata/<model_id>/<version>', methods=['GET'])
def route_get_model_metadata(model_id, version):
    try:
        model_info = model_repo.get_model_info(model_id, version)
        return jsonify(model_info.get('metadata', {}))
    except Exception as e:
        current_app.logger.error(f"Error getting model metadata: {str(e)}")
        raise InvalidUsage('Error getting model metadata', status_code=500, payload={'details': str(e)})

@bp.route('/update_model_metadata/<model_id>/<version>', methods=['PUT'])
def route_update_model_metadata(model_id, version):
    try:
        new_metadata = request.json
        print(f"Received update request for model {model_id} version {version}")
        print(f"New metadata: {new_metadata}")

        current_info = model_repo.get_model_info(model_id, version)
        print(f"Current info: {current_info}")

        # Update only the fields provided in new_metadata that exist in current_info
        updated_info = {**current_info, **{k: v for k, v in new_metadata.items() if k in current_info}}
        print(f"Updated info before sending to update_model_metadata: {updated_info}")

        updated_info = model_repo.update_model_metadata(model_id, version, updated_info)
        print(f"Update successful. Updated info: {updated_info}")

        return jsonify(updated_info)
    except ValueError as ve:
        error_message = str(ve)
        print(f"ValueError: {error_message}")
        if "Invalid manifest" in error_message:
            print(f"Current manifest structure: {current_info}")
            print("Expected manifest structure: ModelMetadata fields")
        return jsonify({"error": "Invalid manifest", "message": error_message}), 400
    except KeyError as ke:
        error_message = f"Missing key in manifest: {str(ke)}"
        print(error_message)
        return jsonify({"error": "Invalid manifest structure", "message": error_message}), 400
    except Exception as e:
        print(f"Unexpected error updating model metadata: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": "Internal server error", "message": str(e)}), 500