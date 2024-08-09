from dataclasses import dataclass, asdict, field
from typing import List, Optional, Dict, Any

@dataclass
class ModelVersionMetadata:
    model_id: str
    file_name: str
    file_type: str
    file_cid: str
    created_at: str
    major_version: int
    minor_version: int
    description: Optional[str] = None
    authors: List[str] = field(default_factory=list)
    license: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    framework: Optional[str] = None
    task_type: Optional[str] = None
    dataset: Optional[str] = None
    metrics: Dict[str, float] = field(default_factory=dict)
    hyperparameters: Dict[str, Any] = field(default_factory=dict)
    input_shape: Optional[List[int]] = None
    output_shape: Optional[List[int]] = None
    model_type: Optional[str] = None

    @property
    def name(self):
        return f"{self.version}_{self.model_id}"

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