from fastapi import FastAPI, BackgroundTasks
from pydantic import BaseModel
from image_tools import process_document_from_url
from utils import extract_fv_invoice_data, extract_wz_data
import httpx

app = FastAPI(title="OCR Invoice Service")

class ExtractRequest(BaseModel):
    file_url: str
    forward_url: str | None = None

async def send_result_async(forward_url: str, result: dict):
    """
    Asynchronously sends result to forward_url
    """
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(forward_url, json=result)
            print(f"✅ Result forwarded to {forward_url}, status: {response.status_code}")
    except Exception as e:
        print(f"❌ Failed to forward result to {forward_url}: {str(e)}")

@app.post("/extract_fv")
async def extract_invoice(data: ExtractRequest, background_tasks: BackgroundTasks):
    """
    Accepts URL to PDF or PNG invoice file,
    performs OCR and returns JSON with invoice details.
    Optionally forwards result to forward_url included in JSON body.
    """
    try:
        text_output = await process_document_from_url(data.file_url)
        result = extract_fv_invoice_data(text_output)
        
        if data.forward_url:
            background_tasks.add_task(send_result_async, data.forward_url, result)
            return {
                "status": "processed",
                "message": "Result is being forwarded asynchronously",
                "data": result
            }
        return result
    except Exception as e:
        return {"error": str(e)}

@app.post("/extract_wz")
async def extract_wz(data: ExtractRequest, background_tasks: BackgroundTasks):
    """
    Accepts URL to WZ / Delivery Note (Dokument Dostawy),
    performs OCR and returns JSON with delivery details.
    Optionally forwards result to forward_url included in JSON body.
    """
    try:
        text_output = await process_document_from_url(data.file_url)
        result = extract_wz_data(text_output)
        
        if data.forward_url:
            background_tasks.add_task(send_result_async, data.forward_url, result)
            return {
                "status": "processed",
                "message": "Result is being forwarded asynchronously",
                "data": result
            }
        return result
    except Exception as e:
        return {"error": str(e)}
