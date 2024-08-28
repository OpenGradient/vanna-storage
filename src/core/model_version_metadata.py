from dataclasses import dataclass, field
import os
from typing import Optional, Dict, Any, Self
from uuid import UUID
from datetime import datetime, timezone
from core.models import CoreModel

@dataclass
class FileMetadata:
    filename: str
    file_type: str
    file_cid: str
    file_size: str
    created_at: str

    @staticmethod
    def is_valid_metadata(metadata: dict[str, Any]) -> bool:
        assert isinstance(metadata, dict)
        required_keys = FileMetadata.__annotations__.keys()
        return all(key in metadata for key in required_keys)

@dataclass
class ModelVersionMetadataBase(CoreModel):
    ipfs_uuid: str
    version: str
    created_at: str
    release_notes: str | None = None


@dataclass
class ModelVersionMetadata(ModelVersionMetadataBase):
    files: Dict[str, Dict[str, str]] = field(default_factory=dict)
    
    def add_file(self, filename: str, file_cid: str, file_size: int):
        file_type = os.path.splitext(filename)[1][1:].lower()
        self._add_file_dict(filename=filename, metadata={
            "filename": filename,
            "file_type": file_type,
            "file_cid": file_cid,
            "file_size": str(file_size),
            "created_at": datetime.now(timezone.utc).isoformat()
        })
    
    def _add_file_dict(self, filename: str, metadata: dict[str, Any]):
        assert FileMetadata.is_valid_metadata(metadata)
        self.files[filename] = metadata

