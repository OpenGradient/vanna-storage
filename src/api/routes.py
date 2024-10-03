from flask import Blueprint, request, Response, current_app, jsonify, stream_with_context
from api.ipfs_client import IPFSClient
import logging
from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename 
import time
import importlib
import os
import tempfile
import zipfile
from io import BytesIO
import struct
from onnx import onnx_pb
from collections import namedtuple
import io

bp = Blueprint('api', __name__)

ipfs_client = IPFSClient()

def load_onnx():
    try:
        return importlib.import_module('onnx')
    except ImportError:
        current_app.logger.warning("ONNX is not installed. ONNX file parsing will be disabled.")
        return None

# Define structures for ONNX parsing
TensorInfo = namedtuple('TensorInfo', ['name', 'data_type', 'dims'])

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def read_onnx_header_from_stream(stream):
    try:
        magic_number = stream.read(4)
        if magic_number != b'ONNX':
            raise ValueError(f"Not a valid ONNX file. Magic number: {magic_number}")
        
        version = struct.unpack('<I', stream.read(4))[0]
        
        header = onnx_pb.ModelProto()
        header_size = struct.unpack('<Q', stream.read(8))[0]
        header_bytes = stream.read(header_size)
        header.ParseFromString(header_bytes)
        
        if not header.IsInitialized():
            raise ValueError("ONNX header is not fully initialized")
        
        return header, magic_number + struct.pack('<I', version) + struct.pack('<Q', header_size) + header_bytes
    except Exception as e:
        logger.error(f"Error in read_onnx_header_from_stream: {str(e)}")
        raise

def onnx_file_generator(file: FileStorage):
    is_header_parsed = False
    header = None
    
    def generate():
        nonlocal is_header_parsed, header
        if not is_header_parsed:
            try:
                header, header_bytes = read_onnx_header_from_stream(file.stream)
                is_header_parsed = True
                yield header_bytes
            except Exception as e:
                logger.error(f"Error parsing ONNX header: {str(e)}")
                raise
        
        while True:
            chunk = file.stream.read(8192)  # Read in 8KB chunks
            if not chunk:
                break
            yield chunk
    
    return generate(), header

@bp.route('/upload', methods=['POST'])
def upload():
    try:
        file = request.files.get('file')
        if not file:
            return jsonify({"error": "No file part in the request"}), 400

        if file.filename.lower().endswith('.onnx'):
            filename = secure_filename(file.filename)
            
            try:
                file_generator, header = onnx_file_generator(file)
                
                if header is None:
                    raise ValueError("Failed to parse ONNX header")
                
                # Extract metadata from header
                metadata = {
                    "ir_version": header.ir_version,
                    "producer_name": header.producer_name,
                    "producer_version": header.producer_version,
                    "domain": header.domain,
                    "model_version": header.model_version,
                    "doc_string": header.doc_string,
                    "metadata_props": [(prop.key, prop.value) for prop in header.metadata_props]
                }
                
                # Extract input and output information
                def get_type_info(value_info):
                    return {
                        "name": value_info.name,
                        "type": onnx_pb.TensorProto.DataType.Name(value_info.type.tensor_type.elem_type),
                        "shape": [dim.dim_value if dim.HasField('dim_value') else None 
                                  for dim in value_info.type.tensor_type.shape.dim]
                    }
                
                metadata["input_types"] = [get_type_info(inp) for inp in header.graph.input]
                metadata["output_types"] = [get_type_info(out) for out in header.graph.output]
                
                # Upload to IPFS
                cid = ipfs_client.add_stream(file_generator, filename)
                
                return jsonify({
                    "cid": cid,
                    "metadata": metadata
                })
            except ValueError as ve:
                logger.error(f"Error parsing ONNX file: {str(ve)}")
                return jsonify({"error": f"Error parsing ONNX file: {str(ve)}"}), 400
            except Exception as e:
                logger.error(f"Error uploading to IPFS: {str(e)}")
                return jsonify({"error": f"Error uploading to IPFS: {str(e)}"}), 500

        else:
            return jsonify({"error": "Invalid file type"}), 400

    except Exception as e:
        logger.error(f"Upload failed: {str(e)}")
        return jsonify({"error": str(e)}), 500

def is_stream_requested():
    return request.args.get('stream', '').lower() == 'true'

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