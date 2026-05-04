from pydantic import BaseModel, Field
from typing import List

class Activity(BaseModel):
    name: str
    component: type

class Activities(BaseModel):
    idx: int = 0
    screens: List[Activity] = Field(default_factory=list)
