# Lightweight Python base
FROM python:3.11-slim

# Avoid Python buffering and ensure predictable logs
ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Install Python deps first for better layer caching
COPY requirements.txt /app/requirements.txt
RUN pip install --upgrade pip \
    && pip install -r requirements.txt

# Copy the rest of the app
COPY . /app

# Expose app port
EXPOSE 8000

# Start FastAPI app with Uvicorn
CMD ["uvicorn", "ux.app:app", "--host", "0.0.0.0", "--port", "8000"]
