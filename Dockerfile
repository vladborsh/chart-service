# Chart Service - Trading Signal Chart Generator API

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies for matplotlib
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY indicators.py .
COPY chart_renderer.py .
COPY api_server.py .

# Create non-root user for security
RUN useradd -m -u 1000 chartuser && \
    chown -R chartuser:chartuser /app

# Switch to non-root user
USER chartuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health')" || exit 1

# Run the API server
CMD ["python", "api_server.py"]
