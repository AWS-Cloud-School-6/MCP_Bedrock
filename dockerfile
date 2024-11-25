# Base image
FROM python:3.9-slim

# Set environment variables
ENV FLASK_APP=app.py
ENV FLASK_ENV=development
ENV S3_BUCKET_NAME=aiwa-terraform
ENV GOOGLE_APPLICATION_CREDENTIALS=/tmp/gcp_credential.json

# Set working directory
WORKDIR /app

# Copy application files
COPY . /app

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose the application port
EXPOSE 5000

# Run the application
CMD ["flask", "run", "--host=0.0.0.0", "--port=5000"]
