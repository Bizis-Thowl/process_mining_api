from pydantic import BaseModel, Field

class BasicResponse(BaseModel):

    answer: str = Field(..., description="Antwort auf die Frage.")
    reason: str = Field(..., description="Begründung für die Antwort.")