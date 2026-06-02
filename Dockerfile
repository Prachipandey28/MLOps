# Use python:3.9-slim as the recommended base image
FROM python:3.9-slim

# Set environment variables to prevent Python from writing pyc files and to buffer stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set the working directory in the container
WORKDIR /app

# Copy the dependencies file to the working directory
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the pipeline code, dataset, and configuration into the container
COPY run.py config.yaml data.csv ./

# Make the run.py script executable
RUN chmod +x run.py

# Set the entrypoint to execute the pipeline
ENTRYPOINT ["python", "run.py", "--input", "data.csv", "--config", "config.yaml", "--output", "metrics.json", "--log-file", "run.log"]
