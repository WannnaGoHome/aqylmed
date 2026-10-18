import json
import shutil
import subprocess
from pathlib import Path

import soundfile as sf

ALLOWED_EXTENSIONS = {
    ".wav", ".mp3", ".m4a", ".mp4", ".aac", ".ogg", ".oga", ".opus", ".webm", ".flac",
}
# Форматы, которые без ffmpeg может прочитать libsndfile (для диаризации и нарезки).
_NATIVE_EXTENSIONS = {".wav", ".flac", ".ogg", ".oga"}


class AudioError(Exception):
    """Проблема с аудиофайлом; текст можно показывать пользователю."""


def ffmpeg_available() -> bool:
    return shutil.which("ffmpeg") is not None


def probe_duration(path: str | Path) -> float | None:
    path = Path(path)
    if shutil.which("ffprobe"):
        try:
            out = subprocess.run(
                ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "json", str(path)],
                capture_output=True, text=True, timeout=60, check=True,
            ).stdout
            value = json.loads(out).get("format", {}).get("duration")
            if value is not None:
                return float(value)
        except (subprocess.SubprocessError, ValueError, OSError):
            pass
    try:
        return float(sf.info(str(path)).duration)
    except (RuntimeError, OSError):
        return None


def normalize_audio(src: Path, dest_dir: Path, stem: str) -> Path:
    """Приводит запись к моно 16 кГц FLAC: это хорошо для Whisper/pyannote и сильно уменьшает размер.

    Исходный файл после успешной конвертации удаляется (минимизация хранимых данных).
    Без ffmpeg принимаются только WAV/FLAC/OGG — они сохраняются как есть.
    """
    dest_dir.mkdir(parents=True, exist_ok=True)
    suffix = src.suffix.lower()

    if not ffmpeg_available():
        if suffix not in _NATIVE_EXTENSIONS:
            raise AudioError(
                "На сервере не установлен ffmpeg: поддерживаются только WAV, FLAC и OGG. "
                "Установите ffmpeg или загрузите запись в одном из этих форматов."
            )
        dest = dest_dir / f"{stem}{suffix}"
        shutil.move(str(src), dest)
        return dest

    dest = dest_dir / f"{stem}.flac"
    try:
        subprocess.run(
            ["ffmpeg", "-y", "-i", str(src), "-vn", "-ac", "1", "-ar", "16000", "-c:a", "flac", str(dest)],
            capture_output=True, check=True, timeout=900,
        )
    except subprocess.CalledProcessError as exc:
        dest.unlink(missing_ok=True)
        raise AudioError(
            "Не удалось прочитать аудио: файл повреждён или формат не поддерживается."
        ) from exc
    except subprocess.TimeoutExpired as exc:
        dest.unlink(missing_ok=True)
        raise AudioError("Конвертация аудио заняла слишком много времени.") from exc

    src.unlink(missing_ok=True)
    return dest


def slice_audio(src: str | Path, start: float, end: float, dest: Path) -> Path:
    """Вырезает фрагмент [start, end] секунд в отдельный FLAC-файл."""
    info = sf.info(str(src))
    first = max(0, int(start * info.samplerate))
    last = min(info.frames, int(end * info.samplerate))
    data, rate = sf.read(str(src), start=first, stop=last, dtype="float32")
    sf.write(str(dest), data, rate, format="FLAC")
    return dest
