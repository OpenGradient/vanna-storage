import requests
import os
import random
import string
import time
import io
import json
import itertools
import tempfile
import shutil
import pytest

BASE_URL = "http://localhost:5002"  # Adjust this if your server is running on a different port

TEMP_DIR = tempfile.mkdtemp()

import signal
import sys

def signal_handler(sig, frame):
    print('You pressed Ctrl+C!')
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)

@pytest.fixture(scope="module")
def test_files():
    sizes_mb = [1, 100, 1024, 5120, 10240]
    os.makedirs(TEMP_DIR, exist_ok=True)
    files = generate_test_files(sizes_mb)
    yield files
    # Cleanup
    for file_path in files.values():
        if os.path.exists(file_path):
            os.remove(file_path)
    if os.path.exists(TEMP_DIR):
        os.rmdir(TEMP_DIR)

def generate_test_files(sizes_mb):
    files = {}
    for size_mb in sizes_mb:
        file_name = f"test_file_{size_mb}MB.bin"
        file_path = os.path.join(TEMP_DIR, file_name)
        print(f"Creating file: {file_path}")
        create_random_file(size_mb, file_path)
        if os.path.exists(file_path):
            files[size_mb] = file_path
        else:
            print(f"Failed to create file: {file_path}")
    return files

def create_random_file(size_mb, file_path):
    total_size = size_mb * 1024 * 1024
    with open(file_path, 'wb') as f:
        if size_mb >= 1024:  # Use sparse file for 1GB and larger
            f.seek(total_size - 1)
            f.write(b'\0')
        else:
            chunk_size = 1024 * 1024  # 1MB chunks
            for _ in range(size_mb):
                f.write(os.urandom(chunk_size))

def generate_random_chunk(chunk_size):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=chunk_size)).encode()

def generate_random_file_stream(size_mb):
    total_bytes = size_mb * 1024 * 1024
    bytes_generated = 0
    chunk_size = 8192  # 8KB chunks

    while bytes_generated < total_bytes:
        remaining = total_bytes - bytes_generated
        chunk = os.urandom(min(chunk_size, remaining))
        bytes_generated += len(chunk)
        yield chunk

def generate_random_file(size_mb, file_path):
    total_size = size_mb * 1024 * 1024
    with open(file_path, 'wb') as f:
        f.seek(total_size - 1)
        f.write(b'\0')
    return file_path

class FileStreamWrapper:
    def __init__(self, size_mb):
        self.total_size = size_mb * 1024 * 1024
        self.generator = generate_random_file_stream(size_mb)
        self.bytes_read = 0

    def read(self, chunk_size=-1):
        if self.bytes_read >= self.total_size:
            return b''
        
        if chunk_size == -1:
            chunk_size = self.total_size - self.bytes_read

        chunk = b''
        while len(chunk) < chunk_size:
            try:
                new_data = next(self.generator)
                chunk += new_data
                if len(chunk) > chunk_size:
                    excess = len(chunk) - chunk_size
                    self.generator = itertools.chain([chunk[chunk_size:]], self.generator)
                    chunk = chunk[:chunk_size]
            except StopIteration:
                break

        self.bytes_read += len(chunk)
        return chunk

    def __len__(self):
        return self.total_size

@pytest.mark.skip(reason="Helper function, not a test")
def test_upload_file(file_stream, file_name, total_size):
    url = f"{BASE_URL}/upload"
    files = {'file': (file_name, file_stream, 'application/octet-stream')}
    try:
        start_time = time.time()
        print(f"Starting upload for file: {file_name}, size: {total_size} bytes")
        response = requests.post(url, files=files, data={'stream': 'true'})
        upload_time = time.time() - start_time
        
        print(f"Response status code: {response.status_code}")
        print(f"Response content: {response.text}")
        
        response.raise_for_status()
        
        data = response.json()
        cid = data.get('cid')
        reported_size = data.get('size', 0)
        
        print(f"Reported uploaded size: {reported_size} bytes")
        print(f"Expected size: {total_size} bytes")
        print(f"Upload time: {upload_time:.2f} seconds")
        
        if reported_size != total_size:
            print(f"Warning: Reported uploaded size ({reported_size}) doesn't match expected size ({total_size})")
        
        return cid, upload_time
    except requests.exceptions.RequestException as e:
        print(f"Upload failed: {e}")
        if hasattr(e, 'response'):
            print(f"Response status code: {e.response.status_code}")
            print(f"Response content: {e.response.text}")
        else:
            print("No response received")
        return None, 0

@pytest.mark.skip(reason="Helper function, not a test")
def test_download_raw(cid):
    url = f"{BASE_URL}/download_raw?cid={cid}"
    start_time = time.time()
    response = requests.get(url, stream=True)
    if response.status_code == 200:
        total_size = int(response.headers.get('Content-Length', 0))
        downloaded_size = 0
        for chunk in response.iter_content(chunk_size=8192):
            downloaded_size += len(chunk)
        download_time = time.time() - start_time
        print(f"Reported Content-Length: {total_size} bytes")
        print(f"Actual downloaded size: {downloaded_size} bytes")
        print(f"Download time: {download_time:.2f} seconds")
        if total_size != downloaded_size:
            print(f"Warning: Downloaded size ({downloaded_size}) doesn't match Content-Length ({total_size})")
        return downloaded_size, download_time
    print(f"Download failed with status code: {response.status_code}")
    print(f"Response content: {response.content}")
    return None, 0

@pytest.mark.skip(reason="Helper function, not a test")
def test_download_zip(files):
    url = f"{BASE_URL}/download_zip"
    print(f"Sending request to {url}")
    print(f"Files to be included in zip: {list(files.keys())}")
    response = requests.post(url, json={"files": files, "zip_name": "test_zip"}, stream=True)
    print(f"Response status code: {response.status_code}")
    print(f"Response content: {response.content}")
    if response.status_code == 200:
        total_size = 0
        for chunk in response.iter_content(chunk_size=8192):
            total_size += len(chunk)
        print(f"Actual downloaded zip size: {total_size} bytes")
        return total_size
    else:
        print(f"Download zip failed with status code: {response.status_code}")
        print(f"Response content: {response.content}")
        return None

@pytest.mark.parametrize("size_mb", [1, 100, 1024, 5120, 10240])
def test_upload_and_download(test_files, size_mb):
    result = run_upload_test(test_files, size_mb)
    if result:
        print(f"\nFile Size: {result['size_mb']}MB")
        print(f"Upload Time: {result['upload_time']:.2f} seconds")
        print(f"Download Raw Time: {result['download_raw_time']:.2f} seconds")
        print(f"Uploaded Size: {result['uploaded_size']} bytes")
        print(f"Downloaded Raw Size: {result['downloaded_raw_size']} bytes")
        print(f"CID: {result['cid']}")
    else:
        print(f"Upload failed for {size_mb}MB file")

    if size_mb == 10240:  # Run zip download test after the largest file
        test_zip_download(test_files)

def test_zip_download(test_files):
    # Upload files first
    files_dict = {}
    for size_mb, file_path in test_files.items():
        with open(file_path, 'rb') as file_stream:
            cid, _ = test_upload_file(file_stream, os.path.basename(file_path), os.path.getsize(file_path))
        if cid:
            files_dict[f"file_{size_mb}MB.txt"] = cid

    assert files_dict, "No files were successfully uploaded for zip test"

    start_time = time.time()
    zip_size = test_download_zip(files_dict)
    download_time = time.time() - start_time

    assert zip_size is not None, "Zip download failed"
    print(f"\nZip download successful")
    print(f"Download time: {download_time:.2f} seconds")
    print(f"Downloaded zip size: {zip_size} bytes")

def run_upload_test(test_files, size_mb):
    file_path = test_files.get(size_mb)
    if not file_path or not os.path.exists(file_path):
        print(f"Error: File for {size_mb}MB does not exist.")
        return None

    file_name = os.path.basename(file_path)
    total_size = os.path.getsize(file_path)

    print(f"\nTesting file size: {size_mb}MB")

    start_time = time.time()
    if size_mb >= 1024:  # Use FileStreamWrapper for files 1GB and larger
        file_stream = FileStreamWrapper(size_mb)
    else:
        with open(file_path, 'rb') as f:
            file_stream = f.read()
    
    cid, upload_time = test_upload_file(file_stream, file_name, total_size)
    
    if cid is None:
        print(f"Upload failed for {size_mb}MB file")
        return None

    # Test download
    downloaded_size, download_time = test_download_raw(cid)

    return {
        "size_mb": size_mb,
        "upload_time": upload_time,
        "download_raw_time": download_time,
        "uploaded_size": total_size,
        "downloaded_raw_size": downloaded_size,
        "cid": cid
    }

def test_only_zip_download():
    test_small_files_zip_download()

def test_small_files_zip_download():
    # Use only small files for this test
    small_sizes = [1, 10, 50]  # 1MB, 10MB, 50MB
    files_dict = {}

    for size_mb in small_sizes:
        print(f"Creating and uploading {size_mb}MB file")
        file_path = os.path.join(TEMP_DIR, f"test_file_{size_mb}MB.bin")
        create_random_file(size_mb, file_path)

        with open(file_path, 'rb') as file_stream:
            cid, upload_time = test_upload_file(file_stream, os.path.basename(file_path), os.path.getsize(file_path))
        
        if cid:
            files_dict[f"file_{size_mb}MB.bin"] = cid
            print(f"Uploaded {size_mb}MB file. CID: {cid}")
        else:
            print(f"Failed to upload {size_mb}MB file")

    assert files_dict, "No files were successfully uploaded for zip test"

    print("\nStarting zip download test")
    start_time = time.time()
    zip_size = test_download_zip(files_dict)
    download_time = time.time() - start_time

    assert zip_size is not None, "Zip download failed"
    print(f"Zip download successful")
    print(f"Download time: {download_time:.2f} seconds")
    print(f"Downloaded zip size: {zip_size} bytes")

    return zip_size, download_time