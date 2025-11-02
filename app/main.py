from fastapi import FastAPI, Form
from image_tools import process_document_from_url
from utils import extract_invoice_data

app = FastAPI(title="OCR Invoice Service")


@app.post("/extract_fv")
async def extract_invoice(file_url: str = Form(...)):
    """
    Accepts URL to PDF or PNG invoice file,
    performs OCR and returns JSON with invoice details.
    """
    try:
        text_output = await process_document_from_url(file_url)
        result = extract_invoice_data(text_output)
        return result
    except Exception as e:
        return {"error": str(e)}