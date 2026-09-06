# ─────────────────────────────────────────────
# Ever / Tapestry — the container
#
# Every layer, every toolchain, one image. The build container had no
# Ruby and no JDK, which is why layers 3 and 5 were shipped unverified.
# This fixes that: the image carries gcc, g++, python3, ruby, sqlite3,
# node and a JDK, so `docker run ever` verifies the whole stack rather
# than the part that happened to have a compiler.
#
# Codric Enterprise · Ricky (Dreid) · 2026
# ─────────────────────────────────────────────

FROM debian:bookworm-slim

LABEL org.opencontainers.image.title="Ever / Tapestry"
LABEL org.opencontainers.image.description="A language where every value carries how much it is trusted"
LABEL org.opencontainers.image.vendor="Codric Enterprise"
LABEL org.opencontainers.image.authors="Ricky (Dreid)"
LABEL org.opencontainers.image.version="2.3"

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# One layer per concern, ordered least- to most-volatile so the cache
# holds across source edits.
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        gcc \
        g++ \
        make \
        python3 \
        python3-venv \
        ruby-full \
        sqlite3 \
        nodejs \
        default-jdk-headless \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /ever

# Sources last: edits here invalidate nothing above.
COPY . /ever

RUN chmod +x run.sh 2>/dev/null || true

# Verify at build time. An image that ships without its own tests
# passing is an image that ships a claim instead of a result.
RUN ./run.sh || (echo "BUILD VERIFICATION FAILED" && exit 1)

# The self-generating loop is the default entry point.
CMD ["python3", "2-interpreter-python/vowels.py"]
