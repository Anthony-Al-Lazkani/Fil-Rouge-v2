from typing import Optional
from pydantic import BaseModel

class AffiliationCreate(BaseModel):
    author_id: int
    organization_id: Optional[int] = None
    research_item_id: int
