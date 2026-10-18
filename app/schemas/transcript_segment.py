from pydantic import BaseModel


class TranscriptSegment(BaseModel):
    start: float
    end: float
    text: str


class SpeakerTranscriptSegment(BaseModel):
    start: float
    end: float
    speaker: str
    text: str