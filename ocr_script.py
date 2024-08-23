import os
import pytesseract
from pdf2image import convert_from_path

# Ruta al dataset de PDFs
root_folder = "/app/datasets"

def process_pdfs_in_folder(folder_path):
    for root, dirs, files in os.walk(folder_path):
        for file in files:
            if file.endswith('.pdf'):
                pdf_path = os.path.join(root, file)
                
                # Convierte cada página del PDF a una imagen
                images = convert_from_path(pdf_path)
                
                # Extrae el texto de cada imagen
                for i, image in enumerate(images):
                    text = pytesseract.image_to_string(image)
                    print(f"Texto de la página {i + 1} del archivo {file}:\n{text}\n")

# Inicia el procesamiento desde la carpeta root
process_pdfs_in_folder(root_folder)
