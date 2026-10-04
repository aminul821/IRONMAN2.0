FROM python:3.11-slim-bookworm

ENV PIP_NO_CACHE_DIR=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# ffmpeg: music/video downloads, libgomp1: NSFW detector (onnxruntime)
RUN apt-get update && \
    apt-get install -y --no-install-recommends ffmpeg git libgomp1 ca-certificates && \
    rm -rf /var/lib/apt/lists/*

# yt-dlp needs a JavaScript runtime to download from YouTube
COPY --from=denoland/deno:bin /deno /usr/local/bin/deno

WORKDIR /app

COPY requirements.txt .
RUN pip install --upgrade pip wheel "setuptools<81" && \
    pip install -r requirements.txt

COPY . .

CMD ["python3", "-m", "IronRobo"]
