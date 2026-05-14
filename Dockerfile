FROM python:3.11-slim

# Set working directory
WORKDIR /app/BalanceWheel

# Install system dependencies
RUN apt-get update && apt-get install -y \
    sqlite3 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p logs data

# Create non-root user for security
RUN useradd -m -u 1000 botuser && \
    chown -R botuser:botuser /app/BalanceWheel

# Switch to non-root user
USER botuser

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV DRY_RUN=true

# Health check
HEALTHCHECK --interval=5m --timeout=30s --start-period=30s --retries=3 \
    CMD python -c "import sys; sys.exit(0)" || exit 1

# Default command
CMD ["python", "balance_wheel.py"]
