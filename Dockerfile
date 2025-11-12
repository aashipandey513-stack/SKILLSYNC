# SkillSync/Dockerfile

# Use an official Python runtime as a parent image
FROM python:3.10-slim

# === ADD THIS BLOCK ===
# Install system-level audio dependencies
# libsndfile1 is for PySoundFile (librosa's preferred backend)
# ffmpeg is for audioread (librosa's fallback)
RUN apt-get update && apt-get install -y \
    libsndfile1 \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*
# === END OF BLOCK ===

# Set the working directory in the container
WORKDIR /code

# Copy the requirements file into the container
COPY ./requirements.txt /code/requirements.txt

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

# Copy the rest of the application's source code
COPY . /code/

# Expose the port the app runs on (Hugging Face Spaces default)
EXPOSE 7860

# Command to run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "7860"]