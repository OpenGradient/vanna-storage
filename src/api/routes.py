import io
from os import sendfile
from flask import Blueprint, request, Response, jsonify
from api.validators import validate_file
import logging
from core.model_repository import ModelRepository
import traceback

bp = Blueprint('routes', __name__)
model_repo = ModelRepository.get_instance()

@bp.route('/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'ok'}), 200

@bp.route('/upload_model', methods=['POST'])
def upload_model():
    try:
        file = request.files.get('file')
        model_id = request.form.get('model_id')
        version = request.form.get('version')
        
        print(f"Received request: model_id={model_id}, version={version}")
        
        if not file or not model_id or not version:
            return jsonify({'error': 'Missing file, model_id, or version'}), 400
        
        print(f"File received: {file.filename}")
        
        validation_response = validate_file(file)
        if validation_response:
            return validation_response
        
        serialized_model = file.read()
        print(f"Model serialized, size: {len(serialized_model)} bytes")
        
        manifest_cid = model_repo.upload_model(model_id, serialized_model, version)
        print(f"Model uploaded successfully. Manifest CID: {manifest_cid}")
        
        # Update metadata
        metadata = model_repo._get_metadata()
        if 'models' not in metadata:
            metadata['models'] = {}
        if model_id not in metadata['models']:
            metadata['models'][model_id] = {}
        metadata['models'][model_id][version] = manifest_cid
        model_repo._store_metadata(metadata)
        
        return jsonify({'manifest_cid': manifest_cid})
    
    except Exception as e:
        print(f"Error in upload_model: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

import traceback

from flask import Response

@bp.route('/download_model', methods=['GET'])
def download_model():
    model_id = request.args.get('model_id')
    version = request.args.get('version')
    if not model_id or not version:
        return jsonify({"error": "model_id and version are required"}), 400
    
    try:
        model_data = model_repo.download_model(model_id, version)
        return Response(
            model_data,
            mimetype='application/octet-stream',
            headers={
                "Content-Disposition": f"attachment; filename={model_id}_v{version}.onnx"
            }
        )
    except ValueError as e:
        logging.error(f"ValueError in download_model: {str(e)}")
        return jsonify({"error": str(e)}), 404
    except Exception as e:
        logging.error(f"Unexpected error in download_model: {str(e)}")
        logging.error(traceback.format_exc())
        return jsonify({"error": f"An unexpected error occurred: {str(e)}"}), 500

@bp.route('/get_metadata', methods=['GET'])
def get_metadata():
    try:
        metadata = model_repo._get_metadata()
        logging.debug(f"Retrieved metadata in get_metadata route: {metadata}")
        return jsonify(metadata)
    except Exception as e:
        logging.error(f"Error in get_metadata route: {str(e)}", exc_info=True)
        return jsonify({"error": "An unexpected error occurred"}), 500
    
@bp.route('/validate_version', methods=['POST'])
def validate_version():
    try:
        data = request.json
        model_id = data.get('model_id')
        new_version = data.get('new_version')
        
        if not model_id or not new_version:
            return jsonify({'error': 'Missing model_id or new_version'}), 400
        
        is_valid = model_repo.validate_version(model_id, new_version)
        return jsonify({'is_valid': is_valid})
    
    except ValueError as e:
        logging.error(f"Value error in validate_version: {str(e)}")
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logging.error(f"Unexpected error in validate_version: {str(e)}")
        return jsonify({'error': 'An unexpected error occurred'}), 500

@bp.route('/list_versions', methods=['GET'])
def list_versions():
    model_id = request.args.get('model_id')
    logging.debug(f"Received request to list versions for model_id: {model_id}")
    
    if not model_id:
        logging.error("No model_id provided in request")
        return jsonify({"error": "model_id is required"}), 400
    
    try:
        versions = model_repo.list_versions(model_id)
        logging.debug(f"Versions found for model {model_id}: {versions}")
        return jsonify(versions)
    except ValueError as e:
        logging.error(f"Error in list_versions: {str(e)}")
        return jsonify({"error": str(e)}), 404
    except Exception as e:
        logging.error(f"Error in list_versions: {str(e)}", exc_info=True)
        return jsonify({"error": "An unexpected error occurred"}), 500

@bp.route('/list_content', methods=['GET'])
def list_content():
    model_id = request.args.get('model_id')
    version = request.args.get('version')
    if not model_id or not version:
        return jsonify({"error": "model_id and version are required"}), 400
    
    try:
        content = model_repo.get_model_content(model_id, version)
        return jsonify({
            "model_id": model_id,
            "version": version,
            "manifest": {
                "model_cid": content['manifest']['model_cid']
            },
            "content": {
                "model": content['content']['model']
            }
        })
    except ValueError as e:
        logging.error(f"ValueError in list_content: {str(e)}")
        return jsonify({"error": str(e)}), 404
    except Exception as e:
        logging.error(f"Unexpected error in list_content: {str(e)}")
        logging.error(traceback.format_exc())
        return jsonify({"error": "An unexpected error occurred"}), 500

@bp.route('/get_latest_version/<model_id>', methods=['GET'])
def get_latest_version(model_id):
    try:
        latest_version = model_repo.get_latest_version(model_id)
        return jsonify({'latest_version': latest_version})
    
    except ValueError as e:
        logging.error(f"Value error in get_latest_version: {str(e)}")
        return jsonify({'error': str(e)}), 400
    except FileNotFoundError as e:
        logging.error(f"Model not found in get_latest_version: {str(e)}")
        return jsonify({'error': 'Model not found'}), 404
    except Exception as e:
        logging.error(f"Unexpected error in get_latest_version: {str(e)}")
        return jsonify({'error': 'An unexpected error occurred'}), 500

@bp.route('/rollback_version', methods=['POST'])
def rollback_version():
    try:
        data = request.json
        model_id = data.get('model_id')
        version = data.get('version')
        
        if not model_id or not version:
            return jsonify({'error': 'Missing model_id or version'}), 400
        
        success = model_repo.rollback_version(model_id, version)
        return jsonify({'success': success})
    
    except ValueError as e:
        logging.error(f"Value error in rollback_version: {str(e)}")
        return jsonify({'error': str(e)}), 400
    except FileNotFoundError as e:
        logging.error(f"Model or version not found in rollback_version: {str(e)}")
        return jsonify({'error': 'Model or version not found'}), 404
    except Exception as e:
        logging.error(f"Unexpected error in rollback_version: {str(e)}")
        return jsonify({'error': 'An unexpected error occurred'}), 500