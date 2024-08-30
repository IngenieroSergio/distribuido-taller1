FROM python:3.10-slim

# Install dependencies
RUN apt-get update -y --fix-missing && \
    apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-spa \
    poppler-utils \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy application code
COPY . /app

# Set working directory
WORKDIR /app

# Install Python dependencies
RUN pip install --no-cache-dir pytesseract pdf2image psycopg2-binary

# Expose ports (if needed)
EXPOSE 8080

# Command to run the application
CMD ["python", "ocr_script.py"]
