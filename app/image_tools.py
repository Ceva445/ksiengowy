import aiohttp
import tempfile
import os
import mimetypes
from pdf2image import convert_from_path
from PIL import Image
import pytesseract

async def process_document_from_url(file_url: str) -> str:
    """
    Downloads PDF or PNG from URL, performs OCR and returns recognized text.
    """
    # Download file asynchronously
    async with aiohttp.ClientSession() as session:
        async with session.get(file_url) as response:
            if response.status != 200:
                raise Exception("❌ Failed to download file")
            content = await response.read()
            content_type = response.headers.get("Content-Type", "")

    # Determine extension
    extension = mimetypes.guess_extension(content_type)
    if not extension and "." in file_url:
        extension = os.path.splitext(file_url)[1]
    if not extension:
        extension = ".bin"

    # Temporary file
    with tempfile.NamedTemporaryFile(delete=False, suffix=extension) as tmp:
        tmp.write(content)
        tmp_path = tmp.name

    text_output = ""
    try:
        if extension.lower() == ".pdf":
            # If PDF - convert to images
            images = convert_from_path(tmp_path)
            for image in images:
                text_output += pytesseract.image_to_string(image, lang="pol+eng") + "\n"
        else:
            # If PNG or JPG
            image = Image.open(tmp_path)
            text_output = pytesseract.image_to_string(image, lang="pol+eng")
    finally:
        # Delete temporary file
        os.unlink(tmp_path)

    return text_output.strip()