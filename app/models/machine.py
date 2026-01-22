"""GESTIMA - Machine model"""

from pydantic import BaseModel, ConfigDict
from typing import Optional


class Machine(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    name: str
    type: str
    
    max_rpm: int = 4000
    max_diameter: float = 200.0
    max_length: float = 500.0
    has_live_tooling: bool = False
    has_bar_feeder: bool = True
    bar_feeder_max_dia: float = 65.0
    
    hourly_rate: float = 1000.0
    
    notes: Optional[str] = None
