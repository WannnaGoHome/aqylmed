from pydantic import BaseModel, field_validator


class PatientMemoDraft(BaseModel):
    memo_text: str = ""

    @field_validator("memo_text", mode="before")
    @classmethod
    def _none_to_empty(cls, value):
        return "" if value is None else value
