import aiohttp
import tempfile
import os
import mimetypes
from pdf2image import convert_from_path
from PIL import Image, ImageEnhance, ImageFilter
import pytesseract

def preprocess_image(image):
    """
    Preprocess image to improve OCR quality.
    """
    # Convert to grayscale
    image = image.convert('L')
    
    # Increase contrast
    enhancer = ImageEnhance.Contrast(image)
    image = enhancer.enhance(2.0)
    
    # Increase sharpness
    enhancer = ImageEnhance.Sharpness(image)
    image = enhancer.enhance(2.0)
    
    # Binarization (black and white)
    image = image.point(lambda p: 255 if p > 128 else 0)
    
    return image

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
    
    extension = extension.lower()

    # Temporary file
    with tempfile.NamedTemporaryFile(delete=False, suffix=extension) as tmp:
        tmp.write(content)
        tmp_path = tmp.name

    text_output = ""
    try:
        if extension == ".pdf":
            # If PDF - convert to images
            images = convert_from_path(tmp_path, dpi=300)
            
            for i, image in enumerate(images):
                # Preprocess image
                processed_image = preprocess_image(image)
                
                # Special configuration for Tesseract
                custom_config = r'--oem 3 --psm 6 -c preserve_interword_spaces=1'
                
                # Perform OCR with two languages
                page_text = pytesseract.image_to_string(
                    processed_image, 
                    config=custom_config, 
                    lang="pol+eng"
                )
                text_output += page_text + "\n\n"
                
        elif extension in [".png", ".jpg", ".jpeg", ".tiff", ".bmp"]:
            # Process regular images
            image = Image.open(tmp_path)
            processed_image = preprocess_image(image)
            
            custom_config = r'--oem 3 --psm 6 -c preserve_interword_spaces=1'
            text_output = pytesseract.image_to_string(
                processed_image, 
                config=custom_config, 
                lang="pol+eng"
            )
            
        else:
            raise ValueError(f"❌ Unsupported file format: {extension}")
            
    except Exception as e:
        # Delete temporary file in case of error
        os.unlink(tmp_path)
        raise Exception(f"❌ Error during file processing: {str(e)}")
    
    finally:
        # Delete temporary file
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)

    return text_output.strip()