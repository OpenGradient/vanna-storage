from dataclasses import dataclass, asdict, field
from typing import Optional, Dict, Any
from uuid import UUID
from datetime import datetime, timezone

def assert_valid_file_metadata(metadata: dict[str, Any]) -> None:
    assert isinstance(metadata, dict)
    required_keys = ["file_type", "file_cid", "file_size", "created_at"]
    assert all(key in metadata for key in required_keys), f"Not all keys are present in metadata: {metadata} for file"

@dataclass
class ModelVersionMetadata:
    ipfs_uuid: UUID
    created_at: str
    major_version: int
    minor_version: int
    files: Dict[str, Dict[str, str]] = field(default_factory=dict)
    release_notes: Optional[str] = None

    @property
    def name(self):
        return f"{self.version}_{self.ipfs_uuid}"

    @property
    def version(self):
        return f"{self.major_version}.{self.minor_version:02d}"

    def to_dict(self):
        data = asdict(self)
        data['name'] = self.name
        data['version'] = self.version
        return {k: v for k, v in data.items() if v is not None}

    @classmethod
    def from_dict(cls, data):
        return cls(**{k: v for k, v in data.items() if k in cls.__annotations__})
    
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
