# ── ThermaCity Backend ──────────────────────────────────────
# Multi-stage build targeting ARM64 (Oracle Cloud A1)
# but also buildable on x86_64 for local testing.
#
# Stage 1: Install Python deps into a venv
# Stage 2: Slim runtime with only the venv + model + app code
# ────────────────────────────────────────────────────────────

# ── Stage 1: Builder ──
FROM python:3.11-slim AS builder

# System deps needed to compile native extensions (numpy, scikit-learn, shapely)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    g++ \
    libgeos-dev \
    && rm -rf /var/lib/apt/lists/*

# Create virtualenv for clean layer separation
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt


# ── Stage 2: Runtime ──
FROM python:3.11-slim AS runtime

# Runtime deps: libgeos for Shapely, libpq for asyncpg
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgeos-c1v5 \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy virtualenv from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Non-root user for security
RUN groupadd -r thermacity && useradd -r -g thermacity thermacity

WORKDIR /app

# Copy application code
COPY app/ ./app/

# Copy ML model (the .joblib file is ~48 MB)
# In production, ML_MODEL_PATH should point to /app/ml_model/rf_lst_predictor_v1.joblib
COPY --chown=thermacity:thermacity . .

# Switch to non-root user
USER thermacity

# Expose internal port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Start Uvicorn with 1 worker (memory-conscious)
CMD ["uvicorn", "app.main:app", \
     "--host", "0.0.0.0", \
     "--port", "8000", \
     "--workers", "1", \
     "--proxy-headers", \
     "--forwarded-allow-ips", "*"]
