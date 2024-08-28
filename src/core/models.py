from typing import Any, Self
from dataclasses import dataclass, asdict

@dataclass
class CoreModel:
  
  @classmethod
  def from_dict(cls, data: dict[str, Any]) -> Self:
      if cls.is_valid_data(data):
        return cls(**{k: v for k, v in data.items() if k in cls.__annotations__})
      raise ValueError(f"cannot convert data: {data} to {cls.__name__} class")
  
  @classmethod
  def is_valid_data(cls, data: dict[str, Any]) -> bool:
      assert isinstance(data, dict)
      required_keys = cls.__annotations__.keys()
      return all(key in data for key in required_keys)

  def to_dict(self) -> dict[str, Any]:
     return asdict(self)
  