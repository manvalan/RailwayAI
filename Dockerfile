# Usa un'immagine Python ufficiale e leggera
FROM python:3.11-slim

# Installa le dipendenze di sistema (Python + C++ tools)
RUN apt-get update && apt-get install -y \
    build-essential \
    cmake \
    git \
    && rm -rf /var/lib/apt/lists/*

# Imposta la cartella di lavoro
WORKDIR /app

# Copia i file dei requisiti e installa le librerie
# Installiamo torch separatamente per evitare timeout
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu && \
    pip install --no-cache-dir pybind11 gymnasium && \
    pip install --no-cache-dir -r requirements.txt

# Copia tutto il progetto
COPY . .

# Compila il core C++
RUN mkdir -p build && cd build && \
    cmake .. -DCMAKE_BUILD_TYPE=Release && \
    make -j$(nproc) && \
    cp python/*.so $(python3 -c "import site; print(site.getsitepackages()[0])")

# Espone la porta usata da FastAPI (porta interna del container)
EXPOSE 8002

# Comando per avviare il server
CMD ["python", "api/server.py"]
