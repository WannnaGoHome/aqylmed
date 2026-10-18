FROM python:3.12-slim

# ffmpeg нужен для mp3/m4a/webm и сжатия записей; libsndfile — для soundfile
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /srv
COPY requirements.txt requirements-audio.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Диаризация (torch ~2 ГБ). Соберите с --build-arg WITH_AUDIO=1, если нужна pyannote.
ARG WITH_AUDIO=0
RUN if [ "$WITH_AUDIO" = "1" ]; then pip install --no-cache-dir -r requirements-audio.txt; fi

COPY . .
RUN useradd --create-home --uid 10001 aqyl && mkdir -p /srv/storage && chown -R aqyl /srv/storage
USER aqyl

ENV ENVIRONMENT=production UPLOAD_DIR=/srv/storage/audio
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=40s CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/api/health').status==200 else 1)"

# Один воркер: фоновые задачи живут в памяти процесса (см. README, раздел «Масштабирование»)
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
