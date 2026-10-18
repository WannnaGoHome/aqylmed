from app.schemas.diarization_segment import DiarizationSegment
from app.schemas.transcript_segment import (
    SpeakerTranscriptSegment,
    TranscriptSegment,
)

UNKNOWN_SPEAKER = "SPEAKER_UNKNOWN"


class TranscriptAlignmentService:
    # Если сегмент текста не пересекается ни с одной репликой, берём ближайшую, но не дальше этого.
    MAX_NEAREST_GAP = 1.0

    def align(
        self,
        transcript_segments: list[TranscriptSegment],
        diarization_segments: list[DiarizationSegment],
    ) -> list[SpeakerTranscriptSegment]:
        result: list[SpeakerTranscriptSegment] = []

        for text_segment in transcript_segments:
            if not text_segment.text.strip():
                continue

            best_speaker = UNKNOWN_SPEAKER
            best_overlap = 0.0

            for speaker_segment in diarization_segments:
                overlap = self._calculate_overlap(
                    text_segment.start,
                    text_segment.end,
                    speaker_segment.start,
                    speaker_segment.end,
                )

                if overlap > best_overlap:
                    best_overlap = overlap
                    best_speaker = speaker_segment.speaker

            if best_overlap == 0.0 and diarization_segments:
                best_speaker = self._nearest_speaker(text_segment, diarization_segments)

            result.append(
                SpeakerTranscriptSegment(
                    start=text_segment.start,
                    end=text_segment.end,
                    speaker=best_speaker,
                    text=text_segment.text,
                )
            )

        return result

    def _nearest_speaker(
        self,
        text_segment: TranscriptSegment,
        diarization_segments: list[DiarizationSegment],
    ) -> str:
        best_speaker = UNKNOWN_SPEAKER
        best_gap = self.MAX_NEAREST_GAP
        for speaker_segment in diarization_segments:
            gap = max(
                speaker_segment.start - text_segment.end,
                text_segment.start - speaker_segment.end,
                0.0,
            )
            if gap < best_gap:
                best_gap = gap
                best_speaker = speaker_segment.speaker
        return best_speaker

    def _calculate_overlap(
        self,
        start_a: float,
        end_a: float,
        start_b: float,
        end_b: float,
    ) -> float:
        start = max(start_a, start_b)
        end = min(end_a, end_b)

        return max(0.0, end - start)


def format_timestamp(seconds: float) -> str:
    minutes, secs = divmod(max(seconds, 0.0), 60)
    return f"{int(minutes):02d}:{secs:05.2f}"


def build_speaker_transcript(segments: list[SpeakerTranscriptSegment]) -> str:
    """Технический транскрипт в формате, который ожидает промпт: [мм:сс.сс - мм:сс.сс] SPEAKER_00: текст."""
    lines = []
    for segment in segments:
        text = segment.text.strip()
        if not text:
            continue
        lines.append(
            f"[{format_timestamp(segment.start)} - {format_timestamp(segment.end)}] "
            f"{segment.speaker}: {text}"
        )
    return "\n".join(lines)
