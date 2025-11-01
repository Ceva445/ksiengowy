FROM python:3.10-slim

# Встановлюємо системні залежності
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-pol \
    poppler-utils \
    libgl1 \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Робоча директорія
WORKDIR /app

# Копіюємо файли
COPY app/requirements.txt ./requirements.txt

# Встановлюємо Python-залежності
RUN pip install --no-cache-dir -r requirements.txt

# Копіюємо решту коду
COPY app .

# Експонуємо порт
EXPOSE 8000

# Запускаємо FastAPI через Uvicorn
#CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
