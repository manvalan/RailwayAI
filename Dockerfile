# Usa un'immagine Python ufficiale e leggera
FROM python:3.11-slim

# Installa le dipendenze di sistema minime
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Imposta la cartella di lavoro
WORKDIR /app

# Copia i file dei requisiti e installa le librerie
# Installiamo torch separatamente per evitare timeout
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu && \
    pip install --no-cache-dir -r requirements.txt

# Copia tutto il resto del progetto
COPY . .

# Espone la porta usata da FastAPI
EXPOSE 8002

# Comando per avviare il server
CMD ["python", "api/server.py"]
