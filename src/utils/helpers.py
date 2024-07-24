import os
import uuid
from config.model_config import MODEL_FOLDER, ONE_GB_IN_BYTES

def save_temp_file(file):
    temp_file_name = str(uuid.uuid4())
    temp_file_path = os.path.join(MODEL_FOLDER, temp_file_name)
    file.save(temp_file_path)
    return temp_file_path