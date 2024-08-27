from dataclasses import dataclass, field
from typing import Optional, Dict, Any, Self
from uuid import UUID
from datetime import datetime, timezone
from core.models import CoreModel

def assert_valid_file_metadata(metadata: dict[str, Any]) -> None:
    assert isinstance(metadata, dict)
    required_keys = ["file_type", "file_cid", "file_size", "created_at"]
    assert all(key in metadata for key in required_keys), f"Not all keys are present in metadata: {metadata} for file"


@dataclass
class ModelVersionMetadataBase(CoreModel):
    ipfs_uuid: str
    version: str
    created_at: str
    release_notes: str | None = None


@dataclass
class ModelVersionMetadata(ModelVersionMetadataBase):
    files: Dict[str, Dict[str, str]] = field(default_factory=dict)
    
    def add_file(self, file_name: str, file_type: str, file_cid: str, file_size: int):
        self.add_file_dict(file_name=file_name, metadata={
            "file_type": file_type,
            "file_cid": file_cid,
            "file_size": str(file_size),
            "created_at": datetime.now(timezone.utc).isoformat()
        })
    
    def add_file_dict(self, file_name: str, metadata: dict[str, Any]):
        assert_valid_file_metadata(metadata)
        self.files[file_name] = metadata

@dataclass
class FileMetadata:
    filename: str
    file_type: str
    file_cid: str
    file_size: str
    created_at: str