# =============================================================================
# BillAgent Pro - Backend Dockerfile
# =============================================================================
# Multi-stage build for production-ready Python application
#
# Build: docker build -t billagent-backend .
# Run:   docker run -p 8000:8000 billagent-backend
# =============================================================================

FROM python:3.11-slim as base

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONFAULTHANDLER=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    # OpenCV dependencies
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    # Tesseract OCR (optional fallback)
    tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*

# =============================================================================
# Dependencies Stage
# =============================================================================
FROM base as dependencies

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# =============================================================================
# Production Stage
# =============================================================================
FROM dependencies as production

# Create non-root user for security
RUN addgroup --system --gid 1001 appgroup && \
    adduser --system --uid 1001 --gid 1001 appuser

# Copy application code
COPY --chown=appuser:appgroup . .

# Create storage directories
RUN mkdir -p /app/storage/bills && \
    chown -R appuser:appgroup /app/storage

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Default command (FastAPI with uvicorn)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

# =============================================================================
# Development Stage (with hot reload)
# =============================================================================
FROM dependencies as development

# Copy application code
COPY . .

# Create storage directories
RUN mkdir -p /app/storage/bills

# Expose port
EXPOSE 8000

# Development command with reload
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
