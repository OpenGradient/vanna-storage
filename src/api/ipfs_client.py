import requests
import io
import os
import logging
import time
import json

logger = logging.getLogger(__name__)
IPFS_DEFAULT_CHUNK_SIZE = 256 * 1024  # 256KB

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

    def add_stream(self, file_stream, chunk_size=1024*1024):
        logger.info(f"Starting file upload to IPFS. Base URL: {self.base_url}")
        start_time = time.time()

        try:
            params = {
                'stream-channels': 'true',
                'progress': 'false',
                'chunker': f'size-{chunk_size}'
            }

            files = {
                'file': ('filename', file_stream, 'application/octet-stream')
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
            logger.info(f"File upload completed. CID: {final_cid}, Time: {upload_time:.2f} seconds")
            return final_cid

        except Exception as e:
            logger.error(f"Error during file upload: {str(e)}")
            logger.error(f"Response content: {response.content if 'response' in locals() else 'No response'}")
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
        response = self.session.post(f'{self.base_url}/ls', params={'arg': f'/ipfs/{cid}'})
        response.raise_for_status()
        data = response.json()
        
        if 'Objects' in data and len(data['Objects']) > 0:
            object_data = data['Objects'][0]
            if 'Links' in object_data and len(object_data['Links']) > 0:
                # Sum up the sizes of all links
                total_size = sum(link['Size'] for link in object_data['Links'])
                return total_size
            else:
                return object_data.get('Size', 0)
        else:
            raise ValueError("Unexpected response format from IPFS API")