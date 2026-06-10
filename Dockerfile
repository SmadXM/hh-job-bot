FROM python:3.12-slim

WORKDIR /app

# Create data dir for SQLite volume mount
RUN mkdir -p /data

# Install dependencies first (layer cache)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source
COPY . .

# Non-root user for safety
RUN useradd -m -u 1000 botuser \
 && chown -R botuser:botuser /app /data
USER botuser

CMD ["python", "main.py"]
