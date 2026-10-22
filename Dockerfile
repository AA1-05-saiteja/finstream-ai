# =============================================================================
# FinStream AI - Backend & Streaming Pipeline Dockerfile
# =============================================================================
FROM python:3.12-slim

# Install system dependencies including OpenJDK (required for Spark)
RUN apt-get update && apt-get install -y --no-install-recommends \
    default-jre-headless \
    gcc \
    g++ \
    libpq-dev \
    curl \
    netcat-traditional \
    && rm -rf /var/lib/apt/lists/*

# Set Java Home
ENV JAVA_HOME=/usr/lib/jvm/default-java
ENV PATH="${JAVA_HOME}/bin:${PATH}"

WORKDIR /app

# Copy requirements and install Python packages
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source code and model artifacts
COPY . .

# Expose API port
EXPOSE 8000

# Health check against FastAPI health endpoint
HEALTHCHECK --interval=10s --timeout=5s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/health || exit 1

# Default command starts FastAPI backend
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
