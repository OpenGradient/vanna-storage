from flask import Blueprint, request, jsonify, Response, current_app
from core.model_repository import upload_model, download_model, get_metadata, get_model_content
from core.ipfs_client import IPFSClient

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
        return rv

@bp.errorhandler(InvalidUsage)
def handle_invalid_usage(error):
    response = jsonify(error.to_dict())
    response.status_code = error.status_code
    return response

@bp.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Not found"}), 404

@bp.errorhandler(500)
def internal_error(error):
    return jsonify({"error": "Internal server error"}), 500

@bp.route('/upload_model', methods=['POST'])
def route_upload_model():
    file = request.files.get('file')
    model_id = request.form.get('model_id')
    version = request.form.get('version')
    
    if not file or not model_id or not version:
        raise InvalidUsage('Missing file, model_id, or version', status_code=400)
    
    try:
        serialized_model = file.read()
        manifest_cid = upload_model(model_id, serialized_model, version)
        return jsonify({'manifest_cid': manifest_cid})
    except Exception as e:
        current_app.logger.error(f"Error uploading model: {str(e)}")
        raise InvalidUsage('Error uploading model', status_code=500)

@bp.route('/download_model', methods=['GET'])
def route_download_model():
    model_id = request.args.get('model_id')
    version = request.args.get('version')
    if not model_id or not version:
        raise InvalidUsage("model_id and version are required", status_code=400)
    
    try:
        model_data = download_model(model_id, version)
        return Response(
            model_data,
            mimetype='application/octet-stream',
            headers={
                "Content-Disposition": f"attachment; filename={model_id}_v{version}.onnx"
            }
        )
    except Exception as e:
        current_app.logger.error(f"Error downloading model: {str(e)}")
        raise InvalidUsage('Error downloading model', status_code=500)

@bp.route('/get_metadata', methods=['GET'])
def route_get_metadata():
    try:
        metadata = get_metadata()
        return jsonify(metadata)
    except Exception as e:
        current_app.logger.error(f"Error getting metadata: {str(e)}")
        raise InvalidUsage('Error getting metadata', status_code=500)

@bp.route('/get_metadata/<model_id>', methods=['GET'])
def route_get_model_metadata(model_id):
    try:
        metadata = get_metadata()
        if model_id not in metadata['models']:
            raise InvalidUsage(f"Model {model_id} not found", status_code=404)
        return jsonify(metadata['models'][model_id])
    except InvalidUsage:
        raise
    except Exception as e:
        current_app.logger.error(f"Error getting model metadata: {str(e)}")
        raise InvalidUsage('Error getting model metadata', status_code=500)

@bp.route('/get_model/<model_id>/<version>', methods=['GET'])
def route_get_model(model_id, version):
    try:
        model_content = get_model_content(model_id, version)
        return jsonify({"model_content": model_content})
    except Exception as e:
        current_app.logger.error(f"Error getting model content: {str(e)}")
        raise InvalidUsage('Error getting model content', status_code=500)

@bp.route('/inspect_manifest/<model_id>/<version>', methods=['GET'])
def route_inspect_manifest(model_id, version):
    try:
        client = IPFSClient()
        metadata = get_metadata()
        if model_id not in metadata['models'] or version not in metadata['models'][model_id]['versions']:
            raise InvalidUsage(f"No manifest found for {model_id} version {version}", status_code=404)
        manifest_cid = metadata['models'][model_id]['versions'][version]
        manifest = client.get_json(manifest_cid)
        return jsonify({
            "metadata_manifest_cid": manifest_cid,
            "manifest_content": manifest
        })
    except InvalidUsage:
        raise
    except Exception as e:
        current_app.logger.error(f"Error inspecting manifest: {str(e)}")
        raise InvalidUsage('Error inspecting manifest', status_code=500)