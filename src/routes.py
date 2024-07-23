from flask import Blueprint, request, Response, jsonify
from utils import validate_file
import logging
from model_repository import ModelRepository

bp = Blueprint('routes', __name__)
model_repo = ModelRepository()

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
        
        return jsonify({'manifest_cid': manifest_cid})
    
    except Exception as e:
        print(f"Error in upload_model: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@bp.route('/add_model', methods=['POST'])
def add_model():
    try:
        file = request.files.get('file')
        model_id = request.form.get('model_id')
        new_version = request.form.get('new_version')
        
        logging.info(f"Received request: model_id={model_id}, new_version={new_version}")
        
        if not file or not model_id or not new_version:
            return jsonify({'error': 'Missing file, model_id, or new_version'}), 400
        
        validation_response = validate_file(file)
        if validation_response:
            return validation_response
        
        serialized_model = file.read()
        logging.info(f"Model serialized, size: {len(serialized_model)} bytes")
        
        manifest_cid = model_repo.add_model(model_id, serialized_model, new_version)
        logging.info(f"Added new version {new_version} of model {model_id} to IPFS: {manifest_cid}")
        return jsonify({'manifest_cid': manifest_cid})
    
    except ValueError as e:
        logging.error(f"Value error in add_model: {str(e)}")
        return jsonify({'error': str(e)}), 400
    except IOError as e:
        logging.error(f"IO error in add_model: {str(e)}")
        return jsonify({'error': 'File read error'}), 500
    except Exception as e:
        logging.error(f"Unexpected error in add_model: {str(e)}", exc_info=True)
        return jsonify({'error': 'An unexpected error occurred'}), 500

@bp.route('/download_model', methods=['GET'])
def download_model():
    try:
        model_id = request.args.get('model_id')
        version = request.args.get('version')
        
        if not model_id or not version:
            return jsonify({'error': 'Missing model_id or version'}), 400
        
        model_data = model_repo.download_model(model_id, version)
        return Response(model_data, mimetype='application/octet-stream')
    
    except ValueError as e:
        logging.error(f"Value error in download_model: {str(e)}")
        return jsonify({'error': str(e)}), 400
    except FileNotFoundError as e:
        logging.error(f"File not found in download_model: {str(e)}")
        return jsonify({'error': 'Model not found'}), 404
    except Exception as e:
        logging.error(f"Unexpected error in download_model: {str(e)}")
        return jsonify({'error': 'An unexpected error occurred'}), 500

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

@bp.route('/list_versions/<model_id>', methods=['GET'])
def list_versions(model_id):
    try:
        versions = model_repo.list_versions(model_id)
        if versions:
            return jsonify({'versions': versions})
        else:
            return jsonify({'error': f'No versions found for model_id {model_id}'}), 404
    
    except ValueError as e:
        logging.error(f"Value error in list_versions: {str(e)}")
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logging.error(f"Unexpected error in list_versions: {str(e)}")
        return jsonify({'error': 'An unexpected error occurred'}), 500

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