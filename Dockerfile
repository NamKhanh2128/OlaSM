# ---- Stage 1: Build ----
FROM python:3.12-slim AS builder

WORKDIR /app

COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# ---- Stage 2: Production ----
FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg ca-certificates && rm -rf /var/lib/apt/lists/*

# Copy Python packages from builder
COPY --from=builder /root/.local /root/.local

# Make sure scripts in .local are usable
ENV PATH=/root/.local/bin:$PATH

COPY . .

# Create data directory for SQLite database (will be mounted as volume)
RUN mkdir -p /app/data && chmod -R 777 /app/data

# Copy static policy files to a location NOT mounted by volume
# This ensures policies are always available even when /app/data is mounted
RUN mkdir -p /app/config/policies && \
    cp -r /app/data/policies/* /app/config/policies/ && \
    cp -r /app/data/pricing /app/config/ && \
    cp -r /app/data/safety /app/config/ && \
    cp -r /app/data/gazetteer /app/config/ 2>/dev/null || true

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

CMD ["python", "-m", "uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]

