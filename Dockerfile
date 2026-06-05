# ---------------------------------------------------------
# Dockerfile for Two Sum  — Blockchain HW2
# Author: Zenish Borad
# ---------------------------------------------------------

# Base image: official Python 3.12 slim image from Docker Hub
FROM python:3.12-slim

# Set the working directory inside the container
WORKDIR /app

# Copy the solution script from host into the container
COPY solution.py .

# Default command that runs when the container starts
CMD ["python", "solution.py"]

