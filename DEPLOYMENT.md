# Railway AI Scheduler - Deployment Guide

## 🚀 Quick Start

### Local Development

1. **Install dependencies:**
```bash
pip install -r requirements.txt
```

2. **Start API server:**
```bash
python api/server.py
```

3. **Access API:**
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- Health Check: http://localhost:8000/api/v1/health

### Docker Deployment

1. **Build image:**
```bash
docker build -t railway-scheduler-api .
```

2. **Run container:**
```bash
docker run -d \
  --name railway-api \
  -p 8000:8000 \
  -v $(pwd)/models:/app/models:ro \
  railway-scheduler-api
```

3. **Using Docker Compose:**
```bash
docker-compose up -d
```

## 📡 API Endpoints

### Health & Monitoring

#### GET /api/v1/health
Health check endpoint.

**Response:**
```json
{
  "status": "healthy",
  "model_loaded": true,
  "version": "1.0.0",
  "uptime_seconds": 3600.5
}
```

#### GET /api/v1/metrics
Performance metrics.

**Response:**
```json
{
  "total_requests": 1250,
  "successful_optimizations": 1248,
  "failed_optimizations": 2,
  "avg_inference_time_ms": 1.2,
  "model_info": {
    "loaded": true,
    "loaded_at": "2025-11-19T10:30:00",
    "parameters": 1359034
  }
}
```

#### GET /api/v1/model/info
Model information.

**Response:**
```json
{
  "architecture": "LSTM + Attention",
  "parameters": 1359034,
  "input_dim": 80,
  "hidden_dim": 256,
  "num_trains": 50,
  "loaded_at": "2025-11-19T10:30:00"
}
```

### Optimization

#### POST /api/v1/optimize
Optimize train schedule.

**Request:**
```json
{
  "trains": [
    {
      "id": 101,
      "position_km": 15.0,
      "velocity_kmh": 120.0,
      "current_track": 1,
      "destination_station": 3,
      "delay_minutes": 5.0,
      "priority": 8,
      "is_delayed": true
    },
    {
      "id": 102,
      "position_km": 45.0,
      "velocity_kmh": 100.0,
      "current_track": 1,
      "destination_station": 2,
      "delay_minutes": 0.0,
      "priority": 5,
      "is_delayed": false
    }
  ],
  "max_iterations": 100
}
```

**Response:**
```json
{
  "success": true,
  "resolutions": [
    {
      "train_id": 101,
      "time_adjustment_min": -2.5,
      "track_assignment": 1,
      "confidence": 0.92
    }
  ],
  "total_delay_minutes": 2.5,
  "inference_time_ms": 1.1,
  "conflicts_detected": 1,
  "conflicts_resolved": 1,
  "timestamp": "2025-11-19T10:35:22"
}
```

## 🧪 Testing

### Run test suite:
```bash
python api/test_client.py
```

### Manual testing with curl:

**Health check:**
```bash
curl http://localhost:8000/api/v1/health
```

**Optimize:**
```bash
curl -X POST http://localhost:8000/api/v1/optimize \
  -H "Content-Type: application/json" \
  -d '{
    "trains": [
      {
        "id": 1,
        "position_km": 10.0,
        "velocity_kmh": 120.0,
        "current_track": 0,
        "destination_station": 2,
        "delay_minutes": 3.0,
        "priority": 7,
        "is_delayed": true
      }
    ]
  }'
```

## 🏭 Production Deployment

### Requirements
- Python 3.11+
- 2GB RAM minimum
- 1 CPU core minimum
- 500MB disk space

### Environment Variables

```bash
# Model configuration
MODEL_PATH=/app/models/scheduler_supervised_best.pth

# Server configuration
API_HOST=0.0.0.0
API_PORT=8000
API_WORKERS=4

# Logging
LOG_LEVEL=info
LOG_FILE=/app/logs/api.log

# Optional: GPU support
CUDA_VISIBLE_DEVICES=0
```

### Systemd Service (Linux)

Create `/etc/systemd/system/railway-api.service`:

```ini
[Unit]
Description=Railway AI Scheduler API
After=network.target

[Service]
Type=simple
User=railway
WorkingDirectory=/opt/railway-scheduler
Environment="PATH=/opt/railway-scheduler/venv/bin"
ExecStart=/opt/railway-scheduler/venv/bin/uvicorn api.server:app --host 0.0.0.0 --port 8000 --workers 4
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl enable railway-api
sudo systemctl start railway-api
sudo systemctl status railway-api
```

### Nginx Reverse Proxy

```nginx
upstream railway_api {
    server localhost:8000;
}

server {
    listen 80;
    server_name api.railway-scheduler.com;

    location / {
        proxy_pass http://railway_api;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    # Health check endpoint (no auth)
    location /api/v1/health {
        proxy_pass http://railway_api;
        access_log off;
    }
}
```

### Kubernetes Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: railway-scheduler-api
spec:
  replicas: 3
  selector:
    matchLabels:
      app: railway-api
  template:
    metadata:
      labels:
        app: railway-api
    spec:
      containers:
      - name: api
        image: railway-scheduler-api:1.0.0
        ports:
        - containerPort: 8000
        env:
        - name: MODEL_PATH
          value: "/app/models/scheduler_supervised_best.pth"
        resources:
          requests:
            memory: "2Gi"
            cpu: "1000m"
          limits:
            memory: "4Gi"
            cpu: "2000m"
        livenessProbe:
          httpGet:
            path: /api/v1/health
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 30
        readinessProbe:
          httpGet:
            path: /api/v1/health
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 10
        volumeMounts:
        - name: models
          mountPath: /app/models
          readOnly: true
      volumes:
      - name: models
        persistentVolumeClaim:
          claimName: railway-models-pvc
---
apiVersion: v1
kind: Service
metadata:
  name: railway-api-service
spec:
  selector:
    app: railway-api
  ports:
  - protocol: TCP
    port: 80
    targetPort: 8000
  type: LoadBalancer
```

## 📊 Monitoring

### Prometheus Metrics

Add to `server.py`:
```python
from prometheus_client import Counter, Histogram, generate_latest

REQUEST_COUNT = Counter('api_requests_total', 'Total API requests')
INFERENCE_TIME = Histogram('inference_duration_seconds', 'Inference time')

@app.get("/metrics")
async def metrics():
    return Response(generate_latest(), media_type="text/plain")
```

### Grafana Dashboard

Key metrics to monitor:
- Request rate (req/sec)
- Inference latency (p50, p95, p99)
- Error rate (%)
- Model load status
- Memory usage
- CPU usage

### Logging

Logs are written to stdout in JSON format:
```json
{
  "timestamp": "2025-11-19T10:35:22",
  "level": "INFO",
  "message": "Optimization completed",
  "num_trains": 5,
  "resolutions": 2,
  "inference_time_ms": 1.1
}
```

## 🔒 Security

### Authentication (example with API key)

```python
from fastapi import Security, HTTPException
from fastapi.security import APIKeyHeader

API_KEY_HEADER = APIKeyHeader(name="X-API-Key")

async def verify_api_key(api_key: str = Security(API_KEY_HEADER)):
    if api_key != os.getenv("API_KEY"):
        raise HTTPException(status_code=403, detail="Invalid API key")
    return api_key

@app.post("/api/v1/optimize")
async def optimize_schedule(
    request: OptimizationRequest,
    api_key: str = Depends(verify_api_key)
):
    ...
```

### Rate Limiting

```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

@app.post("/api/v1/optimize")
@limiter.limit("100/minute")
async def optimize_schedule(...):
    ...
```

## 🚨 Troubleshooting

### Model not loading
```bash
# Check model file exists
ls -lh models/scheduler_supervised_best.pth

# Check file permissions
chmod 644 models/scheduler_supervised_best.pth

# Check logs
docker logs railway-api
```

### High memory usage
```bash
# Reduce batch size or number of workers
uvicorn api.server:app --workers 2

# Monitor memory
docker stats railway-api
```

### Slow inference
```bash
# Check CPU/GPU usage
htop

# Enable PyTorch optimizations
export OMP_NUM_THREADS=4
export MKL_NUM_THREADS=4
```

## 📈 Performance Tuning

### CPU Optimization
```bash
# Use optimal number of workers
NUM_WORKERS=$((2 * $(nproc) + 1))
uvicorn api.server:app --workers $NUM_WORKERS
```

### GPU Acceleration
```python
# In server.py
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
model = model.to(device)
```

### Caching
```python
from functools import lru_cache

@lru_cache(maxsize=1000)
def cached_inference(train_hash):
    ...
```

## 📚 Additional Resources

- **API Documentation**: http://localhost:8000/docs
- **GitHub Repository**: https://github.com/manvalan/RailwayAI
- **ML Model Details**: See `STRATEGY.md`
- **C++ Library**: See `API_REFERENCE.md`

## 📞 Support

For issues and questions:
- GitHub Issues: https://github.com/manvalan/RailwayAI/issues
- Email: support@railway-scheduler.ai (example)
