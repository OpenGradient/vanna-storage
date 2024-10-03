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

    def add_stream(self, file_generator, filename):
        try:
            files = {
                'file': (filename, file_generator, 'application/octet-stream')
            }
            response = self.session.post(
                f'{self.base_url}/add',
                files=files,
                params={'stream-channels': 'true', 'progress': 'false'}
            )
            response.raise_for_status()
            result = response.json()
            if 'Hash' in result:
                return result['Hash']
            else:
                raise ValueError("IPFS add response does not contain 'Hash'")
        except Exception as e:
            raise Exception(f"Error adding file to IPFS: {str(e)}")

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