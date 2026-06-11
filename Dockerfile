FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY run.py .

# Set default entrypoint execution syntax
ENTRYPOINT ["python", "run.py"]