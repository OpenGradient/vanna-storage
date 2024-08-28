from dataclasses import dataclass, field
import os
from typing import Optional, Dict, Any, Self
from uuid import UUID
from datetime import datetime, timezone
from core.models import CoreModel

@dataclass
class FileMetadata(CoreModel):
    filename: str
    file_type: str
    file_cid: str
    file_size: str
    created_at: str

@dataclass
class ModelVersionMetadata(CoreModel):
    ipfs_uuid: str
    version: str
    created_at: str
    release_notes: str | None = None
    total_size: int | None = None


@dataclass
class ModelVersionMetadataFiles(ModelVersionMetadata):
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
        assert FileMetadata.is_valid_data(metadata)
        self.files[filename] = metadata

