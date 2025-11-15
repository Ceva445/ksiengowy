from fastapi import FastAPI, Form
from image_tools import process_document_from_url
from utils import extract_fv_invoice_data, extract_wz_data
from pydantic import BaseModel


app = FastAPI(title="OCR Invoice Service")

class ExtractRequest(BaseModel):
    file_url: str

@app.post("/extract_fv")
async def extract_invoice(data: ExtractRequest):
    """
    Accepts URL to PDF or PNG invoice file,
    performs OCR and returns JSON with invoice details.
    """
    try:
        text_output = await process_document_from_url(data.file_url)
        result = extract_fv_invoice_data(text_output)
        return result
    except Exception as e:
        return {"error": str(e)}

@app.post("/extract_wz")
async def extract_wz(data: ExtractRequest):
    """
    Accepts URL to WZ / Delivery Note (Dokument Dostawy),
    performs OCR and returns JSON with delivery details.
    """
    try:
        text_output = await process_document_from_url(data.file_url)
        result = extract_wz_data(text_output)
        return result
    except Exception as e:
        return {"error": str(e)}