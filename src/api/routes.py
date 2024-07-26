from flask import Blueprint, request, jsonify, Response
from core.model_repository import upload_model, download_model, get_metadata, validate_version
import traceback

bp = Blueprint('api', __name__)

@bp.route('/upload_model', methods=['POST'])
def route_upload_model():
    try:
        file = request.files.get('file')
        model_id = request.form.get('model_id')
        version = request.form.get('version')
        
        if not file or not model_id or not version:
            return jsonify({'error': 'Missing file, model_id, or version'}), 400
        
        serialized_model = file.read()
        manifest_cid = upload_model(model_id, serialized_model, version)
        
        return jsonify({'manifest_cid': manifest_cid})
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/download_model', methods=['GET'])
def route_download_model():
    model_id = request.args.get('model_id')
    version = request.args.get('version')
    if not model_id or not version:
        return jsonify({"error": "model_id and version are required"}), 400
    
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
        return jsonify({"error": str(e)}), 500

@bp.route('/get_metadata', methods=['GET'])
def route_get_metadata():
    try:
        metadata = get_metadata()
        return jsonify(metadata)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@bp.route('/validate_version', methods=['POST'])
def route_validate_version():
    data = request.json
    model_id = data.get('model_id')
    new_version = data.get('new_version')
    
    if not model_id or not new_version:
        return jsonify({"error": "model_id and new_version are required"}), 400
    
    try:
        is_valid = validate_version(model_id, new_version)
        return jsonify({"is_valid": is_valid})
    except Exception as e:
        return jsonify({"error": str(e)}), 500