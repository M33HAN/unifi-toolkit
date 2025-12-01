# UniFi Toolkit - Multi-stage Docker build

# Stage 1: Build stage
FROM python:3.12-slim as builder

# Set working directory
WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --user -r requirements.txt

# Stage 2: Runtime stage
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Create non-root user for security
RUN useradd -m -u 1000 toolkit && \
    mkdir -p /app/data && \
    chown -R toolkit:toolkit /app

# Copy Python dependencies from builder
COPY --from=builder /root/.local /home/toolkit/.local

# Copy application code
COPY --chown=toolkit:toolkit . .

# Set PATH to include user site-packages
ENV PATH=/home/toolkit/.local/bin:$PATH

# Switch to non-root user
USER toolkit

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health', timeout=5)" || exit 1

# Run the application
CMD ["python", "run.py"]
