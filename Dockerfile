# Use Python 3.11 slim image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies for document processing
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create sessions directory
RUN mkdir -p /opt/copilot/sessions && chmod 755 /opt/copilot/sessions

# Create non-root user for security
RUN useradd -m -u 1000 copilot && \
    chown -R copilot:copilot /app /opt/copilot/sessions

# Switch to non-root user
USER copilot

# Expose port
EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:5000/debug || exit 1

# Run the application
CMD ["python", "app.py"]
