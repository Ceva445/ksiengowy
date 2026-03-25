import asyncio

from fastapi import FastAPI, BackgroundTasks
from pydantic import BaseModel
from image_tools import process_document_from_url
from utils import extract_fv_invoice_data, extract_wz_data

import httpx
import smtplib
from email.mime.text import MIMEText
import os

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime

app = FastAPI(title="OCR Invoice Service")

# =========================
# 🔹 CONFIG
# =========================

RENDER_ENDPOINT = os.getenv("RENDER_ENDPOINT")

SMTP_HOST = os.getenv("SMTP_HOST")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
SMTP_FROM = os.getenv("SMTP_FROM")


scheduler = AsyncIOScheduler(timezone="Europe/Warsaw")


# =========================
# 🔹 MODELS
# =========================

class ExtractRequest(BaseModel):
    file_url: str
    forward_url: str | None = None


class EmailPayload(BaseModel):
    emails: list[str]
    subject: str
    message: str


# =========================
# 🔹 OCR LOGIC
# =========================

async def send_result_async(forward_url: str, result: dict):
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(forward_url, json=result)
            print(f"Result forwarded to {forward_url}, status: {response.status_code}")
    except Exception as e:
        print(f"Failed to forward result to {forward_url}: {str(e)}")


@app.post("/extract_fv")
async def extract_invoice(data: ExtractRequest, background_tasks: BackgroundTasks):
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


# =========================
# 🔹 EMAIL SENDER
# =========================

def send_email_sync(to_email: str, subject: str, message: str):
    msg = MIMEText(message)
    msg["Subject"] = subject
    msg["From"] = SMTP_FROM
    msg["To"] = to_email

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(SMTP_FROM, to_email, msg.as_string())
    except Exception as e:
        print("EMAIL ERROR:", e)


@app.post("/send-emails")
async def send_emails(payloads: list[EmailPayload]):
    for payload in payloads:
        for email in payload.emails:
            send_email_sync(email, payload.subject, payload.message)

    return {"status": "emails sent"}


# =========================
# 🔹 SCHEDULER LOGIC
# =========================

async def fetch_and_send():
    print(f"Job started at {datetime.now()}")

    max_retries = 3
    attempt = 0

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            while attempt <= max_retries:
                response = await client.post(RENDER_ENDPOINT)

                # якщо 500 — пробуємо ще
                if response.status_code == 500:
                    attempt += 1
                    print(f"Attempt {attempt}: Server error 500, retrying...")

                    if attempt > max_retries:
                        print("Max retries exceeded")
                        return

                    await asyncio.sleep(2)  # невелика пауза перед повтором
                    continue

                # інші помилки
                if response.status_code != 200:
                    print("Render error:", response.text)
                    return

                # якщо успішно — виходимо з циклу
                break

            data = response.json()
            notifications = data.get("notifications", [])

            if not notifications:
                print("No emails to send")
                return

            await send_emails([
                EmailPayload(**item) for item in notifications
            ])

            print(f"Emails sent: {len(notifications)} batches")

    except Exception as e:
        print("Scheduler error:", e)
# =========================
# 🔹 SCHEDULER START
# =========================

@app.on_event("startup")
async def start_scheduler():
    print("Scheduler started")

    # Пн-Пт 08:00
    scheduler.add_job(fetch_and_send, "cron", day_of_week="mon-fri", hour=8, minute=0)

    # Пн-Пт 22:30
    scheduler.add_job(fetch_and_send, "cron", day_of_week="mon-fri", hour=22, minute=30)


    # Субота 16:00
    scheduler.add_job(fetch_and_send, "cron", day_of_week="sat", hour=16, minute=0)

    scheduler.start()