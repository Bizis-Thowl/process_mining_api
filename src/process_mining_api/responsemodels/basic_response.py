from pydantic import BaseModel, Field

class BasicResponse(BaseModel):

    answer: str = Field(..., description="Antwort auf die Frage.")
    url: str = Field(...,description="URL mit den relevantesten Inhalten zur gestellten Frage.")
    reason: str = Field(..., description="Begründung für die Antwort und URL.")