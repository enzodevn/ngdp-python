# syntax=docker/dockerfile:1.7

FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /opt/ngdp

RUN groupadd --gid 10001 ngdp \
    && useradd --uid 10001 --gid ngdp --create-home --shell /usr/sbin/nologin ngdp

COPY requirements-api.txt ./

RUN python -m pip install --upgrade pip \
    && python -m pip install --requirement requirements-api.txt

COPY src ./src
COPY data_raw ./data_raw
COPY data_processed ./data_processed
COPY database ./database
COPY main.py ./

RUN mkdir --parents outputs \
    && chown --recursive ngdp:ngdp /opt/ngdp

USER ngdp

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3)"]

CMD ["python", "-m", "uvicorn", "src.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
