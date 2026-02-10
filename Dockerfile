# Use official Python runtime as a parent image
FROM python:3.13.4-slim

# Set working directory in container
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire application
COPY ludo_bot/ /app/

# Set Python to run in unbuffered mode for better logging
ENV PYTHONUNBUFFERED=1

# Run the bot
CMD ["python", "bot.py"]
