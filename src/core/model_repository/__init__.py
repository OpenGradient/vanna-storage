from .base import ModelRepository
from .download import download_model
from .metadata import _get_metadata, _store_metadata, get_manifest_cid
from .upload import upload_model
from .version_management import validate_version, list_versions, get_latest_version
from .content import get_model_content

# Add all the methods to ModelRepository
ModelRepository.download_model = download_model
ModelRepository._get_metadata = _get_metadata
ModelRepository._store_metadata = _store_metadata
ModelRepository.get_manifest_cid = get_manifest_cid
ModelRepository.upload_model = upload_model
ModelRepository.validate_version = validate_version
ModelRepository.list_versions = list_versions
ModelRepository.get_latest_version = get_latest_version
ModelRepository.get_model_content = get_model_content

# Export ModelRepository
__all__ = ['ModelRepository']