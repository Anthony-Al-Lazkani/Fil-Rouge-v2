from typing import Optional
from sqlmodel import SQLModel, Field

class Source(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str  # e.g., "openalex", "arxiv"
    type: str  # e.g., "academic"
    base_url: Optional[str] = None
    is_active: bool = True
