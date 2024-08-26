import os
import pytesseract
from pdf2image import convert_from_path
from concurrent.futures import ThreadPoolExecutor, as_completed
import sqlite3
import time
from datetime import datetime
import multiprocessing

# Ruta al dataset de PDFs
root_folder = "/app/datasets"
db_path = '/app/output/ocr_results.db'

def process_pdf(file_path):
    start_time = time.time()
    images = convert_from_path(file_path)
    file_name = os.path.basename(file_path)

    for i, image in enumerate(images):
        text = pytesseract.image_to_string(image)
        print(f"Texto de la página {i + 1} del archivo {file_name}:\n{text}\n")

    processing_time = time.time() - start_time
    return {
        'file_path': file_path,
        'file_name': file_name,
        'processing_time': processing_time
    }

def store_result_in_db(result, db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO ocr_results (processed_at, file_path, file_name, processing_time) 
        VALUES (?, ?, ?, ?)
    ''', (
        datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        result['file_path'],
        result['file_name'],
        result['processing_time']
    ))

    conn.commit()
    conn.close()

def update_aggregate_data(total_time, total_files, db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO aggregate_data (total_processing_time, total_files_processed)
        VALUES (?, ?)
    ''', (total_time, total_files))

    conn.commit()
    conn.close()

def main():
    # Inicializa la base de datos
    from init_db import init_db
    init_db(db_path)

    # Crear lista de todos los archivos PDF para ser procesados
    pdf_files = []
    for root, _, files in os.walk(root_folder):
        for file in files:
            if file.endswith('.pdf'):
                pdf_files.append(os.path.join(root, file))

    # Configura el número de workers (número de cores a utilizar)
    num_workers = multiprocessing.cpu_count()  # Puedes ajustar esto según tus necesidades
    total_processing_time = 0
    total_files_processed = 0

    with ThreadPoolExecutor(max_workers=num_workers) as executor:
        futures = {executor.submit(process_pdf, file): file for file in pdf_files}
        
        for future in as_completed(futures):
            result = future.result()
            total_processing_time += result['processing_time']
            total_files_processed += 1

            store_result_in_db(result, db_path)
    
    # Almacena los datos agregados
    update_aggregate_data(total_processing_time, total_files_processed, db_path)

if __name__ == '__main__':
    main()
