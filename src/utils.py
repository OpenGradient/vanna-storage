import os
import uuid
from flask import Response
from config import MODEL_FOLDER, ONE_GB_IN_BYTES

def save_temp_file(file):
    temp_file_name = str(uuid.uuid4())
    temp_file_path = os.path.join(MODEL_FOLDER, temp_file_name)
    file.save(temp_file_path)
    return temp_file_path

def validate_file(file):
    if file.filename == '':
        return Response('No selected file', status=400)
    if file.content_length > ONE_GB_IN_BYTES:
        return Response('File size exceeds the limit', status=413)
    return None
