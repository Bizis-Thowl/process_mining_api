from pydantic import BaseModel, Field

class RetrievalResponse(BaseModel):

    answer: str = Field(..., description="Antwort auf die Frage.")
    reason: str = Field(..., description="Begründung für die Antwort.")
    chunk_ids: list[str] = Field(...,exclude = True, description="Chunk_id aus dem Payload, des chunks, die passt")