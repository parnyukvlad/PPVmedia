FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose port (Railway sets PORT env var)
EXPOSE 8000

# Run with shell to expand PORT variable
CMD uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}
