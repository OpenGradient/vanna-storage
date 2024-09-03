from flask import Response
from config.model_config import TEN_GB_IN_BYTES

def validate_file(file):
    if file.filename == '':
        return Response('No selected file', status=400)
    if file.content_length > TEN_GB_IN_BYTES:
        return Response('File size exceeds the limit', status=413)
    return None