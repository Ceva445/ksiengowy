from fastapi import FastAPI, Form
import pytesseract
from pdf2image import convert_from_path
from PIL import Image
import tempfile
import requests
import os
import mimetypes

app = FastAPI(title="OCR Service")

@app.post("/extract_text")
async def extract_text_from_file(file_url: str = Form(...)):
    """
    Приймає URL до PDF або PNG файлу, завантажує його та повертає розпізнаний текст.
    """
    try:
        # Завантажуємо файл
        response = requests.get(file_url)
        if response.status_code != 200:
            return {"error": "Не вдалося завантажити файл"}

        # Визначаємо тип файлу
        content_type = response.headers.get("Content-Type", "")
        extension = mimetypes.guess_extension(content_type)

        # Якщо немає розширення — пробуємо вгадати з URL
        if not extension and "." in file_url:
            extension = os.path.splitext(file_url)[1]

        if not extension:
            extension = ".bin"  # fallback

        # Створюємо тимчасовий файл із правильним розширенням
        with tempfile.NamedTemporaryFile(delete=False, suffix=extension) as tmp:
            tmp.write(response.content)
            tmp_path = tmp.name

        text_output = ""

        if extension.lower() == ".pdf":
            # Конвертуємо PDF у зображення
            images = convert_from_path(tmp_path)
            for image in images:
                text_output += pytesseract.image_to_string(image, lang="pol+eng") + "\n"
        else:
            # Якщо це зображення
            image = Image.open(tmp_path)
            text_output = pytesseract.image_to_string(image, lang="pol+eng")

        os.unlink(tmp_path)
        return {"extracted_text": text_output.strip()}

    except Exception as e:
        return {"error": str(e)}
