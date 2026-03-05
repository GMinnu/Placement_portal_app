FROM python:3.11-slim
WORKDIR /app
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN mkdir -p backend/uploads backend/exports backend/offer_letters
EXPOSE 5000
CMD ["python", "backend/app.py"]

