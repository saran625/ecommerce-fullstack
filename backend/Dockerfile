FROM python:3.11-slim

WORKDIR /app

# Install netcat for health checks
RUN apt-get update && apt-get install -y netcat-openbsd && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

# Make wait script executable
RUN chmod +x wait_for_db.py

EXPOSE 5000

# Wait for DB then start app
CMD ["sh", "-c", "python wait_for_db.py && python app.py"]