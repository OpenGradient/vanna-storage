from flask import Blueprint, request, jsonify, Response, current_app
from core.model_repository import ModelRepository
from core.ipfs_client import IPFSClient
import re
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
    file = request.files.get('file')
    model_id = request.form.get('model_id')
    
    if not file or not model_id:
        raise InvalidUsage('Missing file or model_id', status_code=400)
    
    try:
        serialized_model = file.read()
        manifest_cid, new_version = model_repo.upload_model(model_id, serialized_model)
        return jsonify({'manifest_cid': manifest_cid, 'version': new_version})
    except Exception as e:
        current_app.logger.error(f"Error uploading model: {str(e)}")
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

@bp.route('/model_repo_metadata', methods=['GET'])
def route_get_metadata():
    try:
        metadata = model_repo.get_metadata()
        return jsonify(metadata)
    except Exception as e:
        current_app.logger.error(f"Error getting metadata: {str(e)}")
        raise InvalidUsage('Error getting metadata', status_code=500, payload={'details': str(e)})

@bp.route('/model_metadata/<model_id>', methods=['GET'])
def route_get_model_metadata(model_id):
    try:
        metadata = model_repo.get_metadata()
        if model_id not in metadata['models']:
            raise InvalidUsage(f"Model {model_id} not found", status_code=404)
        return jsonify(metadata['models'][model_id])
    except InvalidUsage:
        raise
    except Exception as e:
        current_app.logger.error(f"Error getting model metadata: {str(e)}")
        raise InvalidUsage('Error getting model metadata', status_code=500, payload={'details': str(e)})

@bp.route('/model_info/<model_id>/<version>', methods=['GET'])
def route_get_model_info(model_id, version):
    try:
        client = IPFSClient()
        metadata = model_repo.get_metadata()
        
        # Enforce the x.yz version format
        version_match = re.match(r'^\d+\.\d{2}$', version)  # Match major and exactly two digits for minor
        if not version_match:
            raise InvalidUsage(f"Invalid version format: {version}. Must be in the form 'x.yz where x, y, and z are integers.'", status_code=400)

        if model_id not in metadata['models'] or version not in metadata['models'][model_id]['versions']:
            raise InvalidUsage(f"No manifest found for {model_id} version {version}", status_code=404)
        
        manifest_cid = metadata['models'][model_id]['versions'][version]
        manifest = client.get_json(manifest_cid)
        
        model_content = model_repo.get_model_content(model_id, version)
        
        return jsonify({
            "metadata_manifest_cid": manifest_cid,
            "manifest_content": manifest,
            "model_content": model_content
        })
    except InvalidUsage:
        raise
    except Exception as e:
        current_app.logger.error(f"Error getting model info: {str(e)}")
        raise InvalidUsage('Error getting model info', status_code=500, payload={'details': str(e)})