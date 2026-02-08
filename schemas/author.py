from typing import Optional
from pydantic import BaseModel


class AuthorCreate(BaseModel):
    name: str
    type: str
    base_url: Optional[str] = None