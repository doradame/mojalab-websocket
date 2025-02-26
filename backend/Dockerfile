# Use official Python base image
FROM python:3.9

# Set working directory inside the container
WORKDIR /app

# Copy application files
COPY . /app

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose the Flask application port
EXPOSE 5050

# Start the Flask application using Eventlet
CMD ["python", "app.py"]