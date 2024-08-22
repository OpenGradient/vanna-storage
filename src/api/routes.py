from flask import Blueprint, request, jsonify, Response, current_app, send_file
from core.model_repository import ModelRepository
from core.ipfs_client import IPFSClient
from packaging import version as parse
import json
import io
import zipfile
import logging
from datetime import datetime, timezone
from mimetypes import guess_type

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
ipfs_client = IPFSClient()

@bp.route('/upload_model', methods=['POST'])
def route_upload_model():
    ipfs_uuid = request.form.get('ipfs_uuid')
    metadata = request.form.get('metadata', '{}')
    release_notes = request.form.get('release_notes')
    
    if not ipfs_uuid:
        return jsonify({'error': 'Missing ipfs_uuid'}), 400
    
    files = request.files
    if not files:
        return jsonify({'error': 'No files uploaded'}), 400

    try:
        metadata_dict = json.loads(metadata)
        file_dict = {file.filename: file for file in files.getlist('files')}
        
        if release_notes is not None:
            metadata_dict['release_notes'] = release_notes
        
        manifest_cid, new_version = model_repo.upload_model(ipfs_uuid, file_dict, metadata_dict)
        
        response = {
            'ipfs_uuid': ipfs_uuid,
            'manifest_cid': manifest_cid,
            'version': new_version,
        }
        if release_notes is not None:
            response['release_notes'] = release_notes
        
        return jsonify(response)
    except json.JSONDecodeError:
        return jsonify({'error': 'Invalid JSON in metadata'}), 400
    except Exception as e:
        current_app.logger.error(f"Error uploading model: {str(e)}")
        return jsonify({'error': 'Error uploading model', 'details': str(e)}), 500

@bp.route('/download_model/<ipfs_uuid>', methods=['GET'])
@bp.route('/download_model/<ipfs_uuid>/<version>', methods=['GET'])
def route_download_model(ipfs_uuid=None, version=None):
    if ipfs_uuid is None:
        ipfs_uuid = request.args.get('ipfs_uuid')

    version = version if version is not None else request.args.get('version')
    if version is None:
        version = model_repo.get_latest_version(ipfs_uuid)
    
    if not ipfs_uuid or not version:
        raise InvalidUsage('Missing ipfs_uuid or version', status_code=400)
    
    try:
        model_files = model_repo.download_model(ipfs_uuid, version)
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for file_name, file_content in model_files.items():
                zip_file.writestr(file_name, file_content)
        zip_buffer.seek(0)
        return Response(zip_buffer.getvalue(), mimetype='application/zip',
                        headers={'Content-Disposition': f'attachment;filename={version}.{ipfs_uuid}.zip'})
    except Exception as e:
        current_app.logger.error(f"Error downloading model: {str(e)}")
        raise InvalidUsage('Error downloading model', status_code=500, payload={'details': str(e)})

@bp.route('/list_versions/<ipfs_uuid>', methods=['GET'])
def route_list_versions(ipfs_uuid):
    try:
        versions = model_repo.list_versions(ipfs_uuid)
        
        if not versions:
            return jsonify({'error': 'No versions found'}), 404

        return sorted(versions, key=lambda v: parse.parse(v), reverse=True)
    except Exception as e:
        current_app.logger.error(f"Error listing versions: {str(e)}")
        raise InvalidUsage('Error listing versions', status_code=500, payload={'details': str(e)})

@bp.route('/latest_version/<ipfs_uuid>', methods=['GET'])
def route_get_latest_version(ipfs_uuid):
    try:
        latest_version = model_repo.get_latest_version(ipfs_uuid)
        return jsonify({'ipfs_uuid': ipfs_uuid, 'latest_version': latest_version})
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

@bp.route('/model_info/<ipfs_uuid>', methods=['GET'])
@bp.route('/model_info/<ipfs_uuid>/<version>', methods=['GET'])
def route_get_model_info(ipfs_uuid, version=None):
    try:
        if version is None:
            version = model_repo.get_latest_version(ipfs_uuid)
        model_info = model_repo.get_model_info(ipfs_uuid, version)
        return jsonify(model_info)
    except Exception as e:
        current_app.logger.error(f"Error getting model info: {str(e)}")
        raise InvalidUsage('Error getting model info', status_code=500, payload={'details': str(e)})

@bp.route('/list_files/<ipfs_uuid>', methods=['GET'])
@bp.route('/list_files/<ipfs_uuid>/<version>', methods=['GET'])
def route_list_files(ipfs_uuid, version=None):
    try:
        file_type = request.args.get('file_type')

        version = version if version is not None else request.args.get('version')
        if version is None:
            version = model_repo.get_latest_version(ipfs_uuid)
        
        model_info = model_repo.get_model_info(ipfs_uuid, version)
        if 'files' not in model_info:
            return jsonify({'error': 'No files found for this model version'}), 404
        
        files_list = []
        for filename, file_info in model_info['files'].items():
            if file_type is None or file_info.get('file_type') == file_type:
                files_list.append({
                    'filename': filename,
                    'file_type': file_info.get('file_type', 'unknown'),
                    'file_cid': file_info.get('file_cid', ''),
                    'created_at': file_info.get('created_at', 'Unknown'),
                    'size': file_info.get('size', 'Unknown')
                })
        
        return jsonify({
            'ipfs_uuid': ipfs_uuid,
            'version': version,
            'files': files_list
        })
    except Exception as e:
        current_app.logger.error(f"Error listing files: {str(e)}")
        return jsonify({'error': 'Error listing files', 'details': str(e)}), 500

@bp.route('/download_file/<file_cid>', methods=['GET'])
def route_download_file(file_cid):
    try:
        file_content = ipfs_client.cat(file_cid)
        
        # Attempt to get the filename from the model info
        filename = "downloaded_file"  # Default filename
        for model_info in model_repo.get_all_objects():
            for file_info in model_info.get('files', {}).values():
                if file_info.get('file_cid') == file_cid:
                    filename = file_info.get('filename', filename)
                    break
            if filename != "downloaded_file":
                break
        
        return Response(
            file_content,
            mimetype='application/octet-stream',
            headers={'Content-Disposition': f'attachment;filename={filename}'}
        )
    except Exception as e:
        current_app.logger.error(f"Error downloading file: {str(e)}")
        return jsonify({'error': 'Error downloading file', 'details': str(e)}), 500

@bp.route('/list_latest_models', methods=['GET'])
def route_list_latest_models():
    try:
        order = request.args.get('order', 'desc').lower()
        if order not in ['asc', 'desc']:
            return jsonify({'error': 'Invalid order parameter. Use "asc" or "desc".'}), 400

        latest_models = model_repo.get_all_latest_models()
        
        # Sort the models by creation date
        sorted_models = sorted(
            latest_models.items(),
            key=lambda x: datetime.fromisoformat(x[1]['created_at'].replace('Z', '+00:00')),
            reverse=(order == 'desc')
        )

        result = [
            {
                'ipfs_uuid': ipfs_uuid,
                'version': info['version'],
                'cid': info['cid'],
                'created_at': info['created_at']
            }
            for ipfs_uuid, info in sorted_models
        ]

        return jsonify(result)
    except Exception as e:
        current_app.logger.error(f"Error listing latest models: {str(e)}")
        return jsonify({'error': 'Error listing latest models', 'details': str(e)}), 500

@bp.route('/raw_content/<file_cid>', methods=['GET'])
def route_get_raw_content(file_cid):
    try:
        file_content = ipfs_client.cat(file_cid)
        
        # Attempt to get the filename and determine content type
        filename = "unknown_file"
        content_type = "application/octet-stream"
        for model_info in model_repo.get_all_objects():
            for file_info in model_info.get('files', {}).values():
                if file_info.get('file_cid') == file_cid:
                    filename = file_info.get('filename', filename)
                    content_type = guess_type(filename)[0] or "application/octet-stream"
                    break
            if filename != "unknown_file":
                break
        
        return Response(
            file_content,
            mimetype=content_type,
            headers={'Content-Disposition': f'inline; filename={filename}'}
        )
    except Exception as e:
        current_app.logger.error(f"Error fetching raw content: {str(e)}")
        return jsonify({'error': 'Error fetching raw content', 'details': str(e)}), 500