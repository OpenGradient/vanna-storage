from dataclasses import dataclass, asdict, field
from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime, timezone

@dataclass
class ModelVersionMetadata:
    ipfs_uuid: UUID
    created_at: str
    major_version: int
    minor_version: int
    files: Dict[str, Dict[str, str]] = field(default_factory=dict)

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
    
    def add_file(self, file_name: str, file_type: str, file_cid: str):
        self.files[file_name] = {
            "file_type": file_type,
            "file_cid": file_cid,
            "created_at": datetime.now(timezone.utc).isoformat()
        }