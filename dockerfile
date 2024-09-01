FROM python:3.10-slim

# Install dependencies
RUN apt-get update -y --fix-missing && \
    apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-spa \
    poppler-utils \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy application code
COPY . /app

# Copy the .env file
COPY .env /app/.env

# Install Python dependencies
RUN pip install --no-cache-dir pytesseract pdf2image psycopg2-binary spacy fastapi uvicorn[standard]

# Download spaCy model for Spanish
RUN python -m spacy download es_core_news_sm

# Expose ports (ensure it matches the port uvicorn will run on)
EXPOSE 8000

# Command to run the application
CMD ["uvicorn", "ocr_script:app", "--host", "0.0.0.0", "--port", "8000"]
