import requests
import os
import logging

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

    def cat(self, cid):
        response = self.session.post(f'{self.base_url}/cat', params={'arg': cid})
        response.raise_for_status()
        return response.content

    def get_file_size(self, cid):
        try:
            url = f'{self.base_url}/files/stat'
            params = {'arg': f'/ipfs/{cid}'}
            logging.info(f"Sending request to {url} with params {params}")
            response = self.session.post(url, params=params)
            logging.info(f"Response status code: {response.status_code}")
            logging.info(f"Response content: {response.text}")
            response.raise_for_status()
            return response.json()['Size']
        except requests.exceptions.RequestException as e:
            logging.error(f"IPFS request failed: {str(e)}")
            raise Exception(f"IPFS request failed: {str(e)}")
        except KeyError:
            logging.error(f"Unexpected response format from IPFS: {response.text}")
            raise Exception("Unexpected response format from IPFS")