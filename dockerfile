# Base image
FROM python:3.11-slim

# Environment variables
ENV PYTHONUNBUFFERED=1

# Install system dependencies needed to build Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    g++ \
    libffi-dev \
    libssl-dev \
    python3-dev \
    curl \
    git \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Set work directory
WORKDIR /app

# Copy requirements first to leverage Docker cache
COPY requirements.txt .

# Upgrade pip, setuptools, wheel, then install dependencies
RUN pip install --upgrade pip setuptools wheel
RUN pip install -r requirements.txt

# Copy project files
COPY . .

# Expose port
EXPOSE 8000

# Collect static files (optional if using static files)
RUN python manage.py collectstatic --noinput

# Default command
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]