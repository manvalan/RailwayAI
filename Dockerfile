# Stage 1: Build C++ Core
FROM ubuntu:22.04 AS builder

# Prevent interactive prompts during build
ENV DEBIAN_FRONTEND=noninteractive

# Install dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    cmake \
    git \
    wget \
    unzip \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Install LibTorch (CPU version for maximum compatibility)
WORKDIR /opt
RUN wget https://download.pytorch.org/libtorch/cpu/libtorch-cxx-shared-with-deps-2.1.0%2Bcpu.zip \
    && unzip libtorch-cxx-shared-with-deps-2.1.0+cpu.zip \
    && rm libtorch-cxx-shared-with-deps-2.1.0+cpu.zip

ENV Torch_DIR=/opt/libtorch

# Build RailwayAI C++ Core
WORKDIR /app/build
COPY . /app
RUN cmake .. -DUSE_LIBTORCH=ON -DCMAKE_BUILD_TYPE=Release \
    && make -j$(nproc)

# Stage 2: Runtime Environment
FROM python:3.11-slim

WORKDIR /app

# Install runtime dependencies for C++ libraries
RUN apt-get update && apt-get install -y \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Copy build artifacts from builder stage
COPY --from=builder /app/python/railway_cpp*.so /app/python/
COPY --from=builder /app/build/railwayai.so* /usr/local/lib/
# If there are standalone binaries, copy them too
# COPY --from=builder /app/build/bin/* /usr/local/bin/

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source
COPY api/ /app/api/
COPY python/ /app/python/
COPY .env* /app/

# Create models directory if not exists (in case it's empty in source)
RUN mkdir -p /app/python/models

# Set up environment
ENV LD_LIBRARY_PATH=/usr/local/lib:/app/python
ENV PYTHONPATH=/app

# Expose API and WebSocket ports
EXPOSE 8002

# Run the server
CMD ["python", "api/fdc_integration_api.py"]
