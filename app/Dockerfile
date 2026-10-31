# Use an explicit, slim stable Python image to keep the footprint low
FROM python:3.11-slim

# Prevent Python from writing .pyc files to disk and enable unbuffered logging
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set up the operational working directory within the workspace container
WORKDIR /app

# Install native system dependencies required to build Python Wheels (e.g., pg_config for psycopg2)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy only the dependency manifest first to maximize Docker layer caching
COPY app/requirements.txt /app/requirements.txt

# Install python requirements natively without accessing cache rings
# Note: For strict air-gapped deployments without external proxies, ensure packages
# are pre-mirrored or vendored inside your network loop.
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r /app/requirements.txt

# Copy the entire app runtime cluster code over to the workspace image
COPY app /app

# Explicitly create an unprivileged system user boundary to drop root vulnerabilities
RUN useradd -u 8888 appuser && chown -R appuser:appuser /app
USER appuser

# Expose the port matching your internal FastAPI configuration
EXPOSE 8000

# Fire up the application worker via uvicorn binding directly to cluster nodes
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
