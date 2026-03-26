FROM python:3.11-slim

WORKDIR /app

# Install system deps
RUN apt-get update && apt-get install -y --no-install-recommends gcc && rm -rf /var/lib/apt/lists/*

# Copy and install
COPY pyproject.toml .
COPY src/ src/
COPY web/ web/
RUN pip install --no-cache-dir .

# Expose port
EXPOSE 8000

# Run
CMD ["uvicorn", "kawasaki_keiba.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
