from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List
import os
import time
import pytesseract
from pdf2image import convert_from_path
from multiprocessing import Pool, cpu_count
import psycopg2
from datetime import datetime
import re
import spacy

# Configura spaCy
nlp = spacy.load("es_core_news_sm")

app = FastAPI()

# Configura la conexión a PostgreSQL usando variables de entorno
conn = psycopg2.connect(
    dbname=os.getenv("DB_NAME"),
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD"),
    host=os.getenv("DB_HOST"),
    port=os.getenv("DB_PORT", 5432)
)

# Llama a la función setup_database al inicio
def setup_database():
    cursor = conn.cursor()
    try:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS processed_files (
                id SERIAL PRIMARY KEY,
                processing_date TIMESTAMP,
                file_path TEXT,
                file_name TEXT,
                processing_time FLOAT,
                publication_date DATE,
                newspaper_name TEXT,
                unidades_militares TEXT[],
                divisiones_politicas TEXT[]
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS processing_summary (
                id SERIAL PRIMARY KEY,
                total_processing_time FLOAT,
                total_files_processed INT
            )
        """)
        conn.commit()
    except Exception as e:
        print(f"Error al crear las tablas: {e}")
    finally:
        cursor.close()

# Ejecutar setup_database para asegurar que las tablas se creen
setup_database()

# Ruta al dataset de PDFs con environment
root_folder = os.getenv("ROOT_FOLDER")
if not root_folder:
    raise ValueError("La variable de entorno ROOT_FOLDER no está configurada.")

# Modelos Pydantic para validación de datos
class ProcessedFile(BaseModel):
    id: int
    processing_date: datetime
    file_path: str
    file_name: str
    processing_time: float
    publication_date: datetime
    newspaper_name: str
    unidades_militares: List[str]
    divisiones_politicas: List[str]

class ProcessingSummary(BaseModel):
    total_processing_time: float
    total_files_processed: int

@app.get("/files/", response_model=List[ProcessedFile])
def read_files():
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM processed_files")
    files = cursor.fetchall()
    cursor.close()
    return [
        ProcessedFile(
            id=row[0],
            processing_date=row[1],
            file_path=row[2],
            file_name=row[3],
            processing_time=row[4],
            publication_date=row[5],
            newspaper_name=row[6],
            unidades_militares=row[7],
            divisiones_politicas=row[8],
        )
        for row in files
    ]

@app.post("/process/")
def process_pdf_endpoint():
    num_cores = min(cpu_count(), 4)
    process_pdfs_concurrently(root_folder, num_cores)
    return {"message": "Processing started"}

@app.get("/summary/", response_model=ProcessingSummary)
def read_summary():
    cursor = conn.cursor()
    cursor.execute("SELECT total_processing_time, total_files_processed FROM processing_summary ORDER BY id DESC LIMIT 1")
    summary = cursor.fetchone()
    cursor.close()

    if summary:
        return ProcessingSummary(
            total_processing_time=summary[0],
            total_files_processed=summary[1]
        )
    else:
        raise HTTPException(status_code=404, detail="Summary data not found")

def extract_publication_date(file_name):
    match = re.search(r'\d{2}-\d{2}-\d{4}', file_name)
    if match:
        return datetime.strptime(match.group(), '%d-%m-%Y').date()
    else:
        print(f"No se pudo extraer la fecha de publicación del archivo: {file_name}")
        return None

def process_pdf(pdf_path):
    start_time = time.time()
    file_name = os.path.basename(pdf_path)
    publication_date = extract_publication_date(file_name)
    newspaper_name = os.path.basename(os.path.dirname(pdf_path))
    extracted_texts = []

    try:
        images = convert_from_path(pdf_path)

        for i, image in enumerate(images):
            text = pytesseract.image_to_string(image)
            extracted_texts.append(text)
        
        full_text = " ".join(extracted_texts)
        doc = nlp(full_text)

        unidades_militares, divisiones_politicas = extract_entities(doc)

        processing_time = time.time() - start_time
        processing_date = datetime.now()

        log_to_db(pdf_path, processing_date, processing_time, publication_date, newspaper_name, unidades_militares, divisiones_politicas)

        return (pdf_path, processing_time, len(extracted_texts))

    except Exception as e:
        print(f"Error procesando {pdf_path}: {e}")
        return None

def extract_entities(doc):
    unidades_militares = []
    divisiones_politicas = []

    keywords_militares = {'batallón', 'brigada', 'escuadrón', 'fuerza de tarea'}
    keywords_politicas = {'departamento', 'ciudad', 'municipio', 'corregimiento', 'vereda'}

    for ent in doc.ents:
        if ent.label_ in ['ORG', 'LOC', 'GPE']:
            if any(keyword in ent.text.lower() for keyword in keywords_militares):
                unidades_militares.append(ent.text)
            if any(keyword in ent.text.lower() for keyword in keywords_politicas):
                divisiones_politicas.append(ent.text)

    return unidades_militares, divisiones_politicas

def log_to_db(pdf_path, processing_date, processing_time, publication_date, newspaper_name, unidades_militares, divisiones_politicas):
    cursor = conn.cursor()
    file_name = os.path.basename(pdf_path)

    if publication_date is None:
        print(f"Saltando la inserción de {file_name} debido a fecha de publicación no encontrada.")
        return

    try:
        cursor.execute("""
            INSERT INTO processed_files (processing_date, file_path, file_name, processing_time, publication_date, newspaper_name, unidades_militares, divisiones_politicas)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (processing_date, pdf_path, file_name, processing_time, publication_date, newspaper_name, unidades_militares, divisiones_politicas))
        conn.commit()
    except Exception as e:
        print(f"Error al registrar en la base de datos: {e}")
    finally:
        cursor.close()

def process_pdfs_concurrently(folder_path, num_cores):
    # Verifica y crea las tablas antes de procesar los PDFs
    setup_database()
    pdf_files = []

    for root, dirs, files in os.walk(folder_path):
        for file in files:
            if file.endswith('.pdf'):
                pdf_files.append(os.path.join(root, file))

    with Pool(processes=num_cores) as pool:
        results = pool.map(process_pdf, pdf_files)

    total_time = sum(result[1] for result in results if result)
    total_files = len([result for result in results if result])
    log_summary_to_db(total_time, total_files)

def log_summary_to_db(total_time, total_files):
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO processing_summary (total_processing_time, total_files_processed)
            VALUES (%s, %s)
        """, (total_time, total_files))
        conn.commit()
    except Exception as e:
        print(f"Error al registrar el resumen en la base de datos: {e}")
    finally:
        cursor.close()