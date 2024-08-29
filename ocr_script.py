import os
import time
import pytesseract
from pdf2image import convert_from_path
from multiprocessing import Pool, cpu_count
import psycopg2
from datetime import datetime

# Configura la conexión a PostgreSQL usando variables de entorno
conn = psycopg2.connect(
    dbname=os.getenv("DB_NAME"),
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD"),
    host=os.getenv("DB_HOST"),
    port=os.getenv("DB_PORT", 5432)
)

# Ruta al dataset de PDFs
root_folder = "/app/datasets"

def process_pdf(pdf_path):
    start_time = time.time()
    try:
        # Convierte cada página del PDF a una imagen
        images = convert_from_path(pdf_path)
        extracted_texts = []

        # Extrae el texto de cada imagen
        for i, image in enumerate(images):
            text = pytesseract.image_to_string(image)
            extracted_texts.append(text)

        processing_time = time.time() - start_time
        log_to_db(pdf_path, processing_time)

        return (pdf_path, processing_time, len(extracted_texts))

    except Exception as e:
        print(f"Error procesando {pdf_path}: {e}")
        return None

def log_to_db(pdf_path, processing_time):
    cursor = conn.cursor()
    processing_date = datetime.now()
    file_name = os.path.basename(pdf_path)
    
    try:
        cursor.execute("""
            INSERT INTO processed_files (processing_date, file_path, file_name, processing_time)
            VALUES (%s, %s, %s, %s)
        """, (processing_date, pdf_path, file_name, processing_time))
        conn.commit()
    except Exception as e:
        print(f"Error al registrar en la base de datos: {e}")
    finally:
        cursor.close()

def setup_database():
    cursor = conn.cursor()
    try:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS processed_files (
                id SERIAL PRIMARY KEY,
                processing_date TIMESTAMP,
                file_path TEXT,
                file_name TEXT,
                processing_time FLOAT
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

def process_pdfs_concurrently(folder_path, num_cores):
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

if __name__ == "__main__":
    num_cores = min(cpu_count(), 4)  # Usa el número de cores que desees
    process_pdfs_concurrently(root_folder, num_cores)
    conn.close()
