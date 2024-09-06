from flask import Blueprint, request, Response, current_app, jsonify, stream_with_context
from api.ipfs_client import IPFSClient
import logging

bp = Blueprint('api', __name__)

ipfs_client = IPFSClient()

def is_stream_requested():
    return request.args.get('stream', '').lower() == 'true'

@bp.route('/upload', methods=['POST'])
def upload():
    try:
        current_app.logger.info("Upload request received")
        
        if 'file' not in request.files:
            current_app.logger.error("No file part in the request")
            return Response('No file part', status=400)
        
        file = request.files['file']

        if file.filename == '':
            current_app.logger.error("No selected file")
            return Response('No selected file', status=400)

        stream = is_stream_requested()

        if stream:
            file_cid = ipfs_client.add_stream(file.stream)
        else:
            file_content = file.read()
            file_cid = ipfs_client.add_bytes(file_content)

        current_app.logger.info(f"Uploaded file to IPFS with CID: {file_cid}")
        return jsonify({"cid": file_cid})
    except Exception as e:
        current_app.logger.error(f"Error in upload: {str(e)}")
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
        file_content = ipfs_client.cat(file_cid)
        return Response(file_content, mimetype='application/octet-stream')
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