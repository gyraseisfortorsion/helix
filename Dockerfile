FROM python:3.12-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 DNA_DATA_DIR=/data DNA_ALLOW_LOCAL_WORKSPACES=false
COPY pyproject.toml ./
COPY api ./api
RUN pip install --no-cache-dir '.[science]'
RUN useradd --create-home helix && mkdir -p /data && chown helix:helix /data
USER helix
EXPOSE 8000
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000", "--no-proxy-headers"]
