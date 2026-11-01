FROM python:3.12-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DNA_DATA_DIR=/data \
    DNA_ALLOW_LOCAL_WORKSPACES=false \
    MPLCONFIGDIR=/tmp/matplotlib
COPY deploy/requirements.lock ./deploy/requirements.lock
RUN pip install --no-cache-dir --require-hashes -r deploy/requirements.lock
COPY pyproject.toml ./
COPY api ./api
COPY deploy/smoke_test.py ./deploy/smoke_test.py
RUN pip install --no-cache-dir --no-deps . \
    && useradd --uid 1000 --create-home helix \
    && mkdir -p /data \
    && chown helix:helix /data
USER helix
EXPOSE 8000
HEALTHCHECK --interval=15s --timeout=5s --start-period=30s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=4).read()"
# Exactly one process: it owns the embedded job worker and the SQLite store.
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--no-proxy-headers", "--timeout-graceful-shutdown", "150"]
