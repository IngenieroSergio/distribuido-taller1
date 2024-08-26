import sqlite3

def init_db(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Crear tabla para almacenar los resultados del OCR
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ocr_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            processed_at TEXT,
            file_path TEXT,
            file_name TEXT,
            processing_time REAL
        )
    ''')

    # Crear tabla para almacenar datos agregados
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS aggregate_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            total_processing_time REAL,
            total_files_processed INTEGER
        )
    ''')

    conn.commit()
    conn.close()

# Inicializar la base de datos al ejecutar el script
if __name__ == '__main__':
    init_db('ocr_results.db')
