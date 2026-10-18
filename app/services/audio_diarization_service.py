import threading
import warnings

warnings.filterwarnings(
    "ignore",
    message=r"\s*torchcodec is not installed correctly.*",
    category=UserWarning,
)

warnings.filterwarnings(
    "ignore",
    message=r"std\(\): degrees of freedom is <= 0.*",
    category=UserWarning,
)

import soundfile as sf

from app.core.config import settings
from app.core.errors import ConfigurationError
from app.schemas.diarization_segment import DiarizationSegment


class AudioDiarizationService:
    """Определяет, кто и когда говорит (pyannote.audio). torch/pyannote нужны только здесь,
    поэтому импортируются лениво: текстовый режим работает и без них."""

    def __init__(self):
        if not settings.hf_token:
            raise ConfigurationError(
                "HF_TOKEN не задан: он нужен для загрузки модели pyannote. "
                "Либо задайте токен, либо отключите диаризацию (DIARIZATION_ENABLED=false)."
            )
        try:
            import torch
            from pyannote.audio import Pipeline
        except ImportError as exc:
            raise ConfigurationError(
                "Не установлены torch/pyannote.audio (pip install -r requirements-audio.txt)."
            ) from exc

        self._torch = torch
        self.pipeline = Pipeline.from_pretrained(
            settings.pyannote_model,
            token=settings.hf_token,
        )
        if torch.cuda.is_available():
            self.pipeline.to(torch.device("cuda"))
        self._lock = threading.Lock()  # один проход за раз: пайплайн не рассчитан на параллельные вызовы

    def diarize(self, audio_path: str) -> list[DiarizationSegment]:
        waveform, sample_rate = sf.read(audio_path, dtype="float32")

        # Если stereo, делаем mono
        if waveform.ndim > 1:
            waveform = waveform.mean(axis=1)

        waveform_tensor = self._torch.from_numpy(waveform).unsqueeze(0)

        with self._lock:
            output = self.pipeline(
                {
                    "waveform": waveform_tensor,
                    "sample_rate": sample_rate,
                },
                num_speakers=settings.num_speakers,
            )

        segments: list[DiarizationSegment] = []

        for turn, speaker in output.speaker_diarization:
            start = float(turn.start)
            end = float(turn.end)

            if end - start < 0.3:
                continue

            segments.append(
                DiarizationSegment(
                    start=start,
                    end=end,
                    speaker=str(speaker),
                )
            )
        return self._merge_same_speaker_segments(segments)

    def _merge_same_speaker_segments(
        self,
        segments: list[DiarizationSegment],
        max_gap: float = 0.4,
    ) -> list[DiarizationSegment]:
        if not segments:
            return []

        merged: list[DiarizationSegment] = [segments[0]]

        for segment in segments[1:]:
            last = merged[-1]

            same_speaker = last.speaker == segment.speaker
            small_gap = segment.start - last.end <= max_gap

            if same_speaker and small_gap:
                merged[-1] = DiarizationSegment(
                    start=last.start,
                    end=segment.end,
                    speaker=last.speaker,
                )
            else:
                merged.append(segment)

        return merged
