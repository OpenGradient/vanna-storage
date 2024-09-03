from dataclasses import dataclass, field
import os
from typing import Any
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
    total_size: int = field(default=0)
    files: dict[str, dict[str, str]] = field(default_factory=dict)
    
    def add_file(self, file_path: str, file_cid: str, file_size: int, file_type: str):
        self.files[file_path] = {
            "filename": os.path.basename(file_path),
            "file_cid": file_cid,
            "file_size": str(file_size),
            "file_type": file_type,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        self.total_size += file_size

