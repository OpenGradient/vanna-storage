from flask import Blueprint, request, Response, current_app, jsonify, stream_with_context
from api.ipfs_client import IPFSClient
import logging
from io import BytesIO
import zipfile
from werkzeug.datastructures import Headers
import json
from werkzeug.datastructures import FileStorage
import time
import tempfile
import os

bp = Blueprint('api', __name__)

ipfs_client = IPFSClient()

def is_stream_requested():
    return request.args.get('stream', '').lower() == 'true'

@bp.route('/upload', methods=['POST'])
def upload():
    try:
        logger = logging.getLogger(__name__)
        logger.info("Upload request received")
        start_time = time.time()

        if 'file' not in request.files:
            logger.error("No file part in the request")
            return Response('No file part', status=400)
        
        file: FileStorage = request.files['file']

        if file.filename == '':
            logger.error("No selected file")
            return Response('No selected file', status=400)

        # Get the file size
        file.seek(0, 2)  # Go to the end of the file
        file_size = file.tell()  # Get the position (size)
        file.seek(0)  # Go back to the start of the file

        logger.info(f"File size: {file_size} bytes")

        try:
            file_cid = ipfs_client.add_stream(file.stream)
        except Exception as e:
            logger.error(f"IPFS upload failed: {str(e)}")
            return Response(f"IPFS upload failed: {str(e)}", status=500)

        total_time = time.time() - start_time
        logger.info(f"Uploaded file to IPFS with CID: {file_cid}, size: {file_size} bytes, total time: {total_time:.2f} seconds")
        return jsonify({"filename": file.filename, "cid": file_cid, "size": file_size, "upload_time": total_time})
    except Exception as e:
        logger.error(f"Error in upload: {str(e)}", exc_info=True)
        return Response(f"Internal Server Error: {str(e)}", status=500)

@bp.route('/download', methods=['GET'])
def download():
    file_cid = request.args.get('cid')

    if not file_cid:
        return Response('Empty CID', 400)

    try:
        stream = is_stream_requested()

        if stream:
            def generate():
                try:
                    for chunk in ipfs_client.cat_stream(file_cid):
                        yield chunk
                except Exception as e:
                    current_app.logger.error(f"Error in streaming: {str(e)}")
                    yield str(e).encode()

            return Response(
                stream_with_context(generate()),
                mimetype='application/octet-stream',
                headers={'Content-Disposition': f'attachment;filename={file_cid}'}
            )
        else:
            file_content = ipfs_client.cat(file_cid)
            return Response(
                file_content,
                mimetype='application/octet-stream',
                headers={'Content-Disposition': f'attachment;filename={file_cid}'}
            )
    except Exception as e:
        current_app.logger.error(f"Error in download: {str(e)}")
        return Response(f"Internal Server Error: {str(e)}", status=500)

@bp.route('/download_raw', methods=['GET'])
def download_raw():
    file_cid = request.args.get('cid')

    if not file_cid:
        return Response('Empty CID', 400)

    try:
        file_size = ipfs_client.get_file_size(file_cid)
        current_app.logger.info(f"File size for CID {file_cid}: {file_size}")
        
        def generate():
            bytes_sent = 0
            for chunk in ipfs_client.cat_stream(file_cid):
                bytes_sent += len(chunk)
                yield chunk
            current_app.logger.info(f"Total bytes sent: {bytes_sent}")

        response = Response(stream_with_context(generate()), mimetype='application/octet-stream')
        response.headers['Content-Length'] = str(file_size)
        return response
    except Exception as e:
        current_app.logger.error(f"Error in download_raw: {str(e)}")
        return Response(f"Internal Server Error: {str(e)}", status=500)

@bp.route('/get_file_size', methods=['GET'])
def get_file_size():
    file_cid = request.args.get('cid')

    if not file_cid:
        current_app.logger.error("No CID provided")
        return jsonify({"error": "No CID provided"}), 400

    try:
        file_size = ipfs_client.get_file_size(file_cid)
        current_app.logger.info(f"Size of file with CID {file_cid}: {file_size} bytes")
        return jsonify({"cid": file_cid, "size": file_size})
    except Exception as e:
        current_app.logger.error(f"Error getting file size for CID {file_cid}: {str(e)}")
        return jsonify({"error": f"Error getting file size: {str(e)}"}), 500

@bp.route('/download_zip', methods=['POST'])
def download_zip():
    data = request.json
    if not data or 'files' not in data:
        current_app.logger.error("Invalid request data")
        return jsonify({"error": "Invalid request data"}), 400

    files = data['files']
    zip_name = data.get('zip_name', 'response')
    
    if not zip_name.lower().endswith('.zip'):
        zip_name = f"{zip_name}.zip"

    current_app.logger.info(f"Creating zip file: {zip_name} with {len(files)} files")

    def generate():
        with tempfile.NamedTemporaryFile(delete=False, suffix='.zip') as temp_zip:
            try:
                with zipfile.ZipFile(temp_zip, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                    for file_name, file_cid in files.items():
                        try:
                            current_app.logger.info(f"Adding file to zip: {file_name} (CID: {file_cid})")
                            content = b''.join(ipfs_client.cat_stream(file_cid))
                            zip_file.writestr(file_name, content)
                            current_app.logger.info(f"Successfully added {file_name} to zip")
                        except Exception as e:
                            current_app.logger.error(f"Error processing file {file_name} with CID {file_cid}: {str(e)}")
                            continue

                temp_zip.flush()
                temp_zip.seek(0)
                
                while True:
                    chunk = temp_zip.read(8192)
                    if not chunk:
                        break
                    yield chunk
            except Exception as e:
                current_app.logger.error(f"Error generating zip file: {str(e)}")
                yield str(e).encode()
            finally:
                temp_zip.close()
                os.unlink(temp_zip.name)

    headers = Headers()
    headers.add('Content-Disposition', 'attachment', filename=zip_name)
    headers.add('Content-Type', 'application/zip')
    
    return Response(
        stream_with_context(generate()),
        mimetype='application/zip',
        headers=headers
    )