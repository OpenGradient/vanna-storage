import requests
import io
import os
import logging
import time
import json

logger = logging.getLogger(__name__)

class IPFSClient:
    def __init__(self):
        ipfs_host = os.environ.get('IPFS_HOST', 'localhost')
        ipfs_port = os.environ.get('IPFS_PORT', '5001')
        self.base_url = f'http://{ipfs_host}:{ipfs_port}/api/v0'
        self.session = requests.Session()
        logging.info(f"IPFS Client initialized with base URL: {self.base_url}")

    def add_bytes(self, data):
        response = self.session.post(f'{self.base_url}/add', files={'file': ('filename', data)})
        response.raise_for_status()
        return response.json()['Hash']

    def add_stream(self, file_stream):
        logger.info("Starting file upload to IPFS")
        start_time = time.time()

        try:
            response = self.session.post(
                f'{self.base_url}/add',
                files={'file': ('filename', file_stream, 'application/octet-stream')},
                params={'stream-channels': 'true', 'pin': 'false'}
            )
            response.raise_for_status()
            result = response.json()
            upload_time = time.time() - start_time
            logger.info(f"File upload completed. CID: {result['Hash']}, Time: {upload_time:.2f} seconds")
            return result['Hash']
        except Exception as e:
            logger.error(f"Error during file upload: {str(e)}")
            raise

    def cat(self, cid):
        response = self.session.post(f'{self.base_url}/cat', params={'arg': cid})
        response.raise_for_status()
        return response.content

    def cat_stream(self, cid):
        response = self.session.post(f'{self.base_url}/cat', params={'arg': cid}, stream=True)
        response.raise_for_status()
        return response.iter_content(chunk_size=8192)

    def get_file_size(self, cid):
        response = self.session.post(f'{self.base_url}/files/stat', params={'arg': f'/ipfs/{cid}'})
        response.raise_for_status()
        return response.json()['Size']

    def chunked_add(self, file_stream, chunk_size=1024*1024):
        logger.info(f"Starting chunked file upload to IPFS. Base URL: {self.base_url}")
        start_time = time.time()

        try:
            # Prepare for chunked upload
            files = {
                'file': ('filename', file_stream, 'application/octet-stream')
            }
            
            # Remove the Content-Type header, let requests set it automatically
            params = {
                'stream-channels': 'true',
                'progress': 'false'
            }

            logger.info(f"Sending POST request to {self.base_url}/add")
            response = self.session.post(
                f'{self.base_url}/add',
                files=files,
                params=params,
                stream=True
            )
            logger.info(f"Response status code: {response.status_code}")
            logger.info(f"Response headers: {response.headers}")
            response.raise_for_status()

            # The response is a stream of JSON objects, the last one contains the final CID
            final_cid = None
            for line in response.iter_lines():
                if line:
                    result = json.loads(line)
                    if 'Hash' in result:
                        final_cid = result['Hash']

            if final_cid is None:
                raise Exception("No CID received from IPFS")

            upload_time = time.time() - start_time
            logger.info(f"Chunked file upload completed. CID: {final_cid}, Time: {upload_time:.2f} seconds")
            return final_cid
        except Exception as e:
            logger.error(f"Error during chunked upload: {str(e)}")
            logger.error(f"Response content: {response.content if 'response' in locals() else 'No response'}")
            raise