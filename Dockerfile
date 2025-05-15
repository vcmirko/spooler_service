# Use an official Python runtime as a parent image
FROM python:3.13-slim

# Set the working directory
WORKDIR /app

# Copy requirements.txt if you have one
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Expose the port the app runs on (change if needed)
ARG API_PORT=5000
EXPOSE ${API_PORT}

# Command to run the API with Gunicorn
CMD ["gunicorn", "flow_processor.api:app", "--bind", "0.0.0.0:${API_PORT}"]