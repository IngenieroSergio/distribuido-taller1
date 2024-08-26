# Usa una imagen base de Python
FROM python:3.10-slim

# Instala las dependencias necesarias
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    poppler-utils \
    sqlite3 \
    --fix-missing \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Instala las bibliotecas de Python necesarias
RUN pip install --no-cache-dir pytesseract pdf2image

# Crea un directorio de trabajo
WORKDIR /app

# Copia tu dataset al contenedor
COPY ./datasets /app/datasets

# Copia el script de OCR y el script de inicialización de la base de datos al contenedor
COPY ./ocr_script.py /app/ocr_script.py
COPY ./init_db.py /app/init_db.py

# Define el comando para ejecutar tu script de OCR
CMD ["python", "ocr_script.py"]
