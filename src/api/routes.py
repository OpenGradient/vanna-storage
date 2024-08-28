from flask import Blueprint, request, jsonify, Response, current_app, Request
from core.model_repository import ModelRepository
from core.model_version_metadata import FileMetadata
from core.ipfs_client import IPFSClient
from packaging import version as parse
import json
import io
import zipfile
from uuid import uuid4
import mimetypes
from typing import Literal, Optional
from datetime import datetime

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
    release_notes = request.form.get('release_notes')
    existing_files_form = request.form.get('existing_files')
    is_major_version_form = request.form.get('is_major_version')
    
    if not ipfs_uuid:
        ipfs_uuid = uuid4()

    files = request.files

    try:
        file_dict = {file.filename: file for file in files.getlist('files')}

        existing_files = None
        if existing_files_form is not None:
            existing_files = json.loads(existing_files_form)
        
        is_major_version = None
        if is_major_version_form is not None:
            is_major_version = json.loads(is_major_version_form)

        manifest_cid, new_version = model_repo.upload_model(
            ipfs_uuid=ipfs_uuid,
            new_files=file_dict,
            existing_files=existing_files,
            release_notes=release_notes,
            is_major_version=bool(is_major_version),
        )
        
        response = {
            'ipfs_uuid': str(ipfs_uuid),
            'manifest_cid': manifest_cid,
            'version': new_version,
        }
        if release_notes is not None:
            response['release_notes'] = release_notes
        
        return jsonify(response)
    except json.JSONDecodeError:
        return jsonify({'error': 'Invalid JSON in metadata'}), 400
    except Exception as e:
        current_app.logger.error(f"Error uploading model in routes: {str(e)}")
        return jsonify({'error': 'Error uploading model', 'details': str(e)}), 500

@bp.route('/download_model/<ipfs_uuid>', methods=['GET'])
@bp.route('/download_model/<ipfs_uuid>/<version>', methods=['GET'])
def route_download_model(ipfs_uuid=None, version=None):
    if ipfs_uuid is None:
        ipfs_uuid = request.args.get('ipfs_uuid')

    version = version if version is not None else request.args.get('version')
    if version is None:
        version = model_repo.get_latest_version_number(ipfs_uuid)
    
    if not ipfs_uuid or not version:
        raise InvalidUsage('Missing ipfs_uuid or version', status_code=400)
    
    try:
        model_files, total_size = model_repo.download_model(ipfs_uuid, version)

        # Stream zip file with estimated total size (will be larger than actual size)
        def generate():
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                for file_name, file_content in model_files.items():
                    zip_file.writestr(file_name, file_content)
                    
                    zip_buffer.seek(0)
                    data = zip_buffer.read()
                    yield data
                    zip_buffer.seek(0)
                    zip_buffer.truncate()
        
        response = Response(generate(), mimetype='application/zip')

        response.headers.add('Content-Disposition', f'attachment;filename={version}.{ipfs_uuid}.zip')
        response.headers.add('Content-Length', str(total_size))

        return response
    except Exception as e:
        current_app.logger.error(f"Error downloading model: {str(e)}")
        raise InvalidUsage('Error downloading model', status_code=500, payload={'details': str(e)})

@bp.route('/list_versions/<ipfs_uuid>', methods=['GET'])
def route_list_versions(ipfs_uuid):
    try:
        versions = model_repo.list_versions(ipfs_uuid)
        
        if not versions or len(versions) == 0:
            return []

        # Remove files dict for cleaner response
        for version in versions:
            version.pop("files", None)

        return sorted(versions, key=lambda v: parse.parse(v["version"]), reverse=True)
    except Exception as e:
        current_app.logger.error(f"Error listing versions: {str(e)}")
        raise InvalidUsage('Error listing versions', status_code=500, payload={'details': str(e)})

@bp.route('/latest_version/<ipfs_uuid>', methods=['GET'])
def route_get_latest_version(ipfs_uuid):
    try:
        latest_version = model_repo.get_latest_version_number(ipfs_uuid)
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
            version = model_repo.get_latest_version_number(ipfs_uuid)
        model_info = model_repo.get_model_info(ipfs_uuid, version)
        return jsonify(model_info)
    except Exception as e:
        current_app.logger.error(f"Error getting model info: {str(e)}")
        raise InvalidUsage('Error getting model info', status_code=500, payload={'details': str(e)})

@bp.route('/list_files/<ipfs_uuid>', methods=['GET'])
@bp.route('/list_files/<ipfs_uuid>/<version>', methods=['GET'])
def route_list_files(ipfs_uuid, version: str | None = None):
    try:
        file_type = request.args.get('file_type')

        version = version if version is not None else request.args.get('version')
        if version is None:
            version = model_repo.get_latest_version_number(ipfs_uuid)
            if version is None:
                return jsonify({'error': 'No files found for this model version'}), 404
        
        model_info = model_repo.get_model_info(ipfs_uuid, version)
        if 'files' not in model_info:
            return jsonify({'error': 'No files found for this model version'}), 404
        
        files_list = []
        for filename, metadata in model_info['files'].items():
            if FileMetadata.is_valid_data(metadata) and file_type is None or metadata.get('file_type') == file_type:
                if 'filename' not in metadata:
                    files_list.append({
                        'filename': filename,
                        **metadata
                    })
                else:
                    files_list.append(metadata)
        
        return jsonify({
            'ipfs_uuid': ipfs_uuid,
            'version': version,
            'files': files_list
        })
    except Exception as e:
        current_app.logger.error(f"Error listing files: {str(e)}")
        return jsonify({'error': 'Error listing files', 'details': str(e)}), 500

def _is_valid_integer(s):
    try:
        int(s)
        return True
    except Exception:
        return False

def _send_file_download(ipfs_uuid: Optional[str], request: Request, display_type: Literal["attachment", "inline"]):
    ipfs_uuid = ipfs_uuid if ipfs_uuid is not None else request.args.get('ipfs_uuid')
    if ipfs_uuid is None:
        raise InvalidUsage('Missing ipfs_uuid', status_code=400)

    version = request.args.get('version')
    if version is None:
        version = model_repo.get_latest_version_number(ipfs_uuid)
        if version is None:
            return jsonify({'error': 'File not found'}), 404

    target_filename = request.args.get("target_filename")
    if target_filename is None:
        raise InvalidUsage('Missing target_filename query arg', status_code=400)

    try:
        model_info = model_repo.get_model_info(ipfs_uuid, version)
        if 'files' not in model_info:
            return jsonify({'error': 'No files found for this model version'}), 404
        if not isinstance(model_info['files'], dict):
            raise Exception("Files is not a dict")

        for filename, metadata in model_info['files'].items():
            assert isinstance(metadata, dict)
            if filename == target_filename:
                assert "file_cid" in metadata, "file_cid key not in files metadata dict"
                assert metadata["file_cid"] is not None, "file_cid key exists in files metadata dict but is None"
                assert isinstance(metadata["file_cid"], str), "file_cid value exists but is not a string"

                file_content = ipfs_client.cat(metadata["file_cid"])
                file_size = metadata.get("file_size", None)

                headers = {'Content-Disposition': f'{display_type};filename={filename}'}
                if (_is_valid_integer(file_size)):
                    headers["Content-Length"] = str(file_size)

                guessed_mimetype = mimetypes.guess_type(filename)
                return Response(
                    file_content,
                    mimetype=guessed_mimetype[0] if guessed_mimetype[0] is not None else 'application/octet-stream',
                    headers=headers
                )

        return jsonify({'error': 'File not found'}), 404
    except Exception as e:
        current_app.logger.error(f"Error downloading model: {str(e)}")
        raise InvalidUsage('Error downloading model', status_code=500, payload={'details': str(e)})

@bp.route('/download_file/<ipfs_uuid>', methods=['GET'])
def route_download_model_file(ipfs_uuid=None):
    return _send_file_download(
        ipfs_uuid=ipfs_uuid,
        request=request,
        display_type="attachment",
    )

@bp.route('/raw_content/<ipfs_uuid>', methods=['GET'])
def route_model_file_raw(ipfs_uuid=None):
    return _send_file_download(
        ipfs_uuid=ipfs_uuid,
        request=request,
        display_type="inline",
    )

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
