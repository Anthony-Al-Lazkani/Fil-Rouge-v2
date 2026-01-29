from typing import Optional
from pydantic import BaseModel


class SourceCreate(BaseModel):
    name: str
    type: str
    base_url: Optional[str] = None