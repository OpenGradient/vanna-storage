from flask import Blueprint, request, Response, current_app, jsonify, stream_with_context
from api.ipfs_client import IPFSClient
import logging
from http import HTTPStatus
from io import BytesIO
import zipfile
from werkzeug.datastructures import Headers
import json
from werkzeug.datastructures import FileStorage
import time
import tempfile
import os
from memory_profiler import profile
import psutil
import onnxruntime as ort

MAX_FILE_SIZE = 10 * 1024 * 1024 * 1024  # 10GB

bp = Blueprint('api', __name__)

ipfs_client = IPFSClient()

def is_stream_requested():
    return request.args.get('stream', '').lower() == 'true'

import onnx
from onnx import ModelProto
import io

def load_onnx():
    try:
        return onnx
    except ImportError:
        current_app.logger.warning("ONNX is not installed. ONNX file parsing will be disabled.")
        return None

def get_type_info(tensor):
    if tensor.type.HasField('tensor_type'):
        elem_type = tensor.type.tensor_type.elem_type
        shape = [dim.dim_value if dim.HasField('dim_value') else None for dim in tensor.type.tensor_type.shape.dim]
        return {
            "name": tensor.name,
            "type": onnx.TensorProto.DataType.Name(elem_type),
            "shape": shape
        }
    elif tensor.type.HasField('sequence_type'):
        return {
            "name": tensor.name,
            "type": "Sequence",
            "elem_type": get_type_info(tensor.type.sequence_type.elem_type)
        }
    elif tensor.type.HasField('map_type'):
        return {
            "name": tensor.name,
            "type": "Map",
            "key_type": onnx.TensorProto.DataType.Name(tensor.type.map_type.key_type),
            "value_type": get_type_info(tensor.type.map_type.value_type)
        }
    else:
        return {"name": tensor.name, "type": "Unknown"}

@bp.route('/upload', methods=['POST'])
@profile
def upload():
    logger = logging.getLogger(__name__)
    logger.info("Upload request received")
    start_time = time.time()

    def log_memory_usage():
        process = psutil.Process()
        mem_info = process.memory_info()
        logger.info(f"Memory usage: {mem_info.rss / 1024 / 1024:.2f} MB")

    log_memory_usage()

    try:
        if 'file' not in request.files:
            logger.error("No file part in the request")
            return Response('No file part', status=400)
        
        file = request.files['file']
        if file.filename == '':
            logger.error("No selected file")
            return Response('No selected file', status=400)

        file_read_start = time.time()
        file_content = file.read()
        file_size = len(file_content)
        file_read_time = time.time() - file_read_start
        logger.info(f"File read completed. Size: {file_size} bytes, Time: {file_read_time:.2f} seconds")
        log_memory_usage()

        input_types = []
        output_types = []

        onnx_parse_time = 0
        if file.filename.lower().endswith('.onnx'):
            onnx_parse_start = time.time()
            try:
                # Create an in-memory file object
                file_object = io.BytesIO(file_content)
                
                # Load the model using ONNX Runtime
                session = ort.InferenceSession(file_object.getvalue())
                
                # Get input and output information
                input_types = [
                    {
                        "name": input.name,
                        "type": input.type,
                        "shape": input.shape
                    } for input in session.get_inputs()
                ]
                output_types = [
                    {
                        "name": output.name,
                        "type": output.type,
                        "shape": output.shape
                    } for output in session.get_outputs()
                ]
                
                onnx_parse_time = time.time() - onnx_parse_start
                logger.info(f"ONNX parsing completed. Time: {onnx_parse_time:.2f} seconds")
            except Exception as e:
                logger.error(f"Error reading ONNX file: {str(e)}")
                input_types = []
                output_types = []
            log_memory_usage()

        ipfs_upload_start = time.time()
        try:
            file_cid = ipfs_client.add_bytes(file_content)
            ipfs_upload_time = time.time() - ipfs_upload_start
            logger.info(f"IPFS upload completed. CID: {file_cid}, Time: {ipfs_upload_time:.2f} seconds")
        except Exception as e:
            logger.error(f"IPFS upload failed: {str(e)}")
            return Response(f"IPFS upload failed: {str(e)}", status=500)

        log_memory_usage()

        total_time = time.time() - start_time
        logger.info(f"Total operation completed. Time: {total_time:.2f} seconds")
        
        response_data = {
            "filename": file.filename,
            "cid": file_cid,
            "size": file_size,
            "total_time": total_time,
            "file_read_time": file_read_time,
            "onnx_parse_time": onnx_parse_time,
            "ipfs_upload_time": ipfs_upload_time,
            "input_types": input_types,
            "output_types": output_types
        }

        return jsonify(response_data)
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