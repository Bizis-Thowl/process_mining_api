from pydantic import BaseModel

class Query(BaseModel):
    full_text: str