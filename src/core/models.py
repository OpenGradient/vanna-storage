from typing import Any, Self
from dataclasses import dataclass, asdict

@dataclass
class CoreModel:
  
  @classmethod
  def from_dict(cls, data: dict[str, Any]) -> Self:
      return cls(**{k: v for k, v in data.items() if k in cls.__annotations__})

  def to_dict(self) -> dict[str, Any]:
     return asdict(self)
  