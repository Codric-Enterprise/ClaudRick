# ReVision — minimal image. No runtime dependencies beyond the standard library.
FROM python:3.12-slim

# Don't buffer stdout/stderr; no .pyc files.
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# Install the package. Copy only what the build needs first for better caching.
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-cache-dir .

# Bind to all interfaces inside the container; override at runtime as needed.
ENV REVISION_HOST=0.0.0.0 \
    REVISION_PORT=8000

EXPOSE 8000

# Provide the API key at runtime, e.g.:
#   docker run -e ANTHROPIC_API_KEY=sk-ant-... -p 8000:8000 revision
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/healthz').status==200 else 1)"

CMD ["revision"]
