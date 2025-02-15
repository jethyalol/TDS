# Use an official Python image as a base
FROM python:3.10-slim

# Set the working directory inside the container
WORKDIR /app

# Copy the application code inside the container
COPY . /app

# Install dependencies
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Expose the application port (FastAPI default is 8000)
EXPOSE 8000

# Define the command to run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]