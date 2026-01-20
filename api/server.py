"""
Railway AI Scheduler - REST API Server

Provides HTTP endpoints for train schedule optimization using the ML model.

Endpoints:
- POST /api/v1/optimize - Optimize train schedule
- GET /api/v1/health - Health check
- GET /api/v1/metrics - Performance metrics
- GET /api/v1/model/info - Model information
"""

import sys
import os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from typing import List, Optional, Dict, Any
import torch
import numpy as np
from datetime import datetime
import time
import asyncio
import logging
from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends, status, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from fastapi.staticfiles import StaticFiles
from python.integration.auth import get_current_user, create_access_token
from fastapi.security import OAuth2PasswordRequestForm

from python.models.scheduler_network import SchedulerNetwork

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI
app = FastAPI(
    title="Railway AI Scheduler API",
    description="ML-powered train schedule optimization",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Servire file statici
app.mount("/static", StaticFiles(directory="api/static"), name="static")

# ==================== Connection Manager ====================

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                pass

manager = ConnectionManager()

async def event_poller():
    """Trasmette aggiornamenti periodici ai client WebSocket"""
    while True:
        try:
            await manager.broadcast({
                "type": "state_update",
                "timestamp": datetime.now().isoformat(),
                "status": "active"
            })
        except Exception:
            pass
        await asyncio.sleep(5)

@app.on_event("startup")
async def startup_event():
    logger.info("Starting Railway AI Scheduler API v2.0.0...")
    load_model()
    asyncio.create_task(event_poller())

@app.websocket("/ws/monitoring")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)

@app.post("/token")
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    if form_data.username == "admin" and form_data.password == "admin":
        access_token = create_access_token(data={"sub": form_data.username})
        return {"access_token": access_token, "token_type": "bearer"}
    raise HTTPException(status_code=401, detail="Incorrect username or password")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global state
model = None
model_config = None
metrics = {
    "total_requests": 0,
    "successful_optimizations": 0,
    "failed_optimizations": 0,
    "total_inference_time_ms": 0.0,
    "avg_inference_time_ms": 0.0,
    "model_loaded_at": None,
}


# ============================================================================
# Request/Response Models
# ============================================================================

class Train(BaseModel):
    """Train state"""
    id: int = Field(..., description="Unique train identifier")
    position_km: float = Field(..., description="Current position in km")
    velocity_kmh: float = Field(..., description="Current velocity in km/h")
    current_track: int = Field(..., description="Current track ID")
    destination_station: int = Field(..., description="Destination station ID")
    delay_minutes: float = Field(0.0, description="Current delay in minutes")
    priority: int = Field(5, ge=1, le=10, description="Priority level (1-10)")
    is_delayed: bool = Field(False, description="Whether train is delayed")


class Track(BaseModel):
    """Track segment"""
    id: int
    length_km: float
    is_single_track: bool
    capacity: int
    station_ids: List[int]


class Station(BaseModel):
    """Railway station"""
    id: int
    name: str
    num_platforms: int


class OptimizationRequest(BaseModel):
    """Request for schedule optimization"""
    trains: List[Train] = Field(..., description="List of trains to optimize")
    tracks: Optional[List[Track]] = Field(None, description="Track configuration (optional)")
    stations: Optional[List[Station]] = Field(None, description="Station configuration (optional)")
    max_iterations: int = Field(100, ge=1, le=1000, description="Max optimization iterations")


class Resolution(BaseModel):
    """Resolution action for a train"""
    train_id: int
    time_adjustment_min: float
    track_assignment: int
    confidence: float = Field(..., ge=0.0, le=1.0)


class OptimizationResponse(BaseModel):
    """Response from optimization"""
    success: bool
    resolutions: List[Resolution]
    total_delay_minutes: float
    inference_time_ms: float
    conflicts_detected: int
    conflicts_resolved: int
    timestamp: str


class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    model_loaded: bool
    version: str
    uptime_seconds: float


class MetricsResponse(BaseModel):
    """Metrics response"""
    total_requests: int
    successful_optimizations: int
    failed_optimizations: int
    avg_inference_time_ms: float
    model_info: Dict


class ModelInfo(BaseModel):
    """Model information"""
    architecture: str
    parameters: int
    input_dim: int
    hidden_dim: int
    num_trains: int
    loaded_at: Optional[str]


# ============================================================================
# Model Management
# ============================================================================

def load_model(checkpoint_path: str = 'models/scheduler_real_world.pth'):
    """Load the trained ML model"""
    global model, model_config, metrics
    
    try:
        # Preferisci modello real-world se esiste, altrimenti fallback a supervised
        if not os.path.exists(checkpoint_path):
            checkpoint_path = 'models/scheduler_supervised_best.pth'
            
        logger.info(f"Loading model from {checkpoint_path}")
        checkpoint = torch.load(checkpoint_path, map_location='cpu')
        
        model_config = checkpoint['config']
        
        model = SchedulerNetwork(
            input_dim=model_config['input_dim'],
            hidden_dim=model_config['hidden_dim'],
            num_trains=model_config['num_trains'],
            num_tracks=model_config['num_tracks'],
            num_stations=model_config['num_stations']
        )
        
        model.load_state_dict(checkpoint['model_state_dict'])
        model.eval()
        
        metrics['model_loaded_at'] = datetime.now().isoformat()
        
        logger.info(f"Model loaded successfully (epoch {checkpoint['epoch']}, "
                   f"val_loss: {checkpoint['val_loss']:.4f})")
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to load model: {e}")
        return False


@app.on_event("startup")
async def startup_event():
    """Initialize model on startup"""
    logger.info("Starting Railway AI Scheduler API...")
    success = load_model()
    if not success:
        logger.warning("Model not loaded - API will return errors")


# ============================================================================
# API Endpoints
# ============================================================================

@app.get("/", tags=["Root"])
async def root():
    """Root endpoint"""
    return {
        "service": "Railway AI Scheduler API",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs"
    }


@app.get("/api/v1/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """Health check endpoint"""
    uptime = time.time() - time.mktime(
        datetime.fromisoformat(metrics['model_loaded_at']).timetuple()
    ) if metrics['model_loaded_at'] else 0.0
    
    return HealthResponse(
        status="healthy" if model is not None else "degraded",
        model_loaded=model is not None,
        version="1.0.0",
        uptime_seconds=uptime
    )


@app.get("/api/v1/metrics", response_model=MetricsResponse, tags=["Metrics"])
async def get_metrics():
    """Get performance metrics"""
    return MetricsResponse(
        total_requests=metrics['total_requests'],
        successful_optimizations=metrics['successful_optimizations'],
        failed_optimizations=metrics['failed_optimizations'],
        avg_inference_time_ms=metrics['avg_inference_time_ms'],
        model_info={
            "loaded": model is not None,
            "loaded_at": metrics['model_loaded_at'],
            "parameters": sum(p.numel() for p in model.parameters()) if model else 0
        }
    )


@app.get("/api/v1/model/info", response_model=ModelInfo, tags=["Model"])
async def get_model_info():
    """Get model information"""
    if model is None:
        raise HTTPException(status_code=503, detail="Model not loaded")
    
    return ModelInfo(
        architecture="LSTM + Attention",
        parameters=sum(p.numel() for p in model.parameters()),
        input_dim=model_config['input_dim'],
        hidden_dim=model_config['hidden_dim'],
        num_trains=model_config['num_trains'],
        loaded_at=metrics['model_loaded_at']
    )


@app.post("/api/v1/optimize", response_model=OptimizationResponse, tags=["Optimization"])
async def optimize_schedule(
    request: OptimizationRequest, 
    background_tasks: BackgroundTasks,
    current_user: str = Depends(get_current_user)
):
    """
    Optimize train schedule using ML model
    
    Returns schedule adjustments to minimize delays and resolve conflicts.
    """
    start_time = time.time()
    
    metrics['total_requests'] += 1
    
    if model is None:
        metrics['failed_optimizations'] += 1
        raise HTTPException(status_code=503, detail="Model not loaded")
    
    try:
        # Prepare input tensors
        num_trains = len(request.trains)
        
        if num_trains > model_config['num_trains']:
            raise HTTPException(
                status_code=400,
                detail=f"Too many trains ({num_trains}), max is {model_config['num_trains']}"
            )
        
        # Encode network state (simplified - could be enhanced)
        network_state = np.zeros(80)
        if request.tracks:
            network_state[0] = len(request.tracks)
        if request.stations:
            network_state[1] = len(request.stations)
        network_state[2] = num_trains
        
        # Encode train states
        train_states = np.zeros((model_config['num_trains'], 8))
        for i, train in enumerate(request.trains):
            train_states[i] = [
                train.position_km / 100.0,
                train.velocity_kmh / 200.0,
                train.delay_minutes / 60.0,
                train.priority / 10.0,
                train.current_track / 20.0,
                train.destination_station / 10.0,
                0.0,
                1.0 if train.is_delayed else 0.0
            ]
        
        # Convert to tensors
        network_tensor = torch.FloatTensor(network_state).unsqueeze(0)
        train_tensor = torch.FloatTensor(train_states).unsqueeze(0)
        
        # Run inference
        with torch.no_grad():
            outputs = model(network_tensor, train_tensor)
        
        # Extract predictions
        time_adjustments = outputs['time_adjustments'][0].numpy()
        track_assignments = outputs['track_assignments'][0].numpy()
        conflict_priorities = outputs['conflict_priorities'][0].numpy()
        
        # Build resolutions
        resolutions = []
        total_delay = 0.0
        
        for i in range(num_trains):
            train = request.trains[i]
            
            time_adj = float(time_adjustments[i])
            track_probs = track_assignments[i]
            track_idx = int(np.argmax(track_probs))
            confidence = float(np.max(conflict_priorities[i]))
            
            # Only include significant adjustments
            if abs(time_adj) > 0.5 or track_idx != train.current_track:
                resolutions.append(Resolution(
                    train_id=train.id,
                    time_adjustment_min=time_adj,
                    track_assignment=track_idx,
                    confidence=min(confidence, 1.0)
                ))
            
            # Calculate adjusted delay
            adjusted_delay = train.delay_minutes + time_adj
            total_delay += max(0.0, adjusted_delay)
        
        # Calculate metrics
        inference_time = (time.time() - start_time) * 1000.0
        
        # Update global metrics
        metrics['successful_optimizations'] += 1
        metrics['total_inference_time_ms'] += inference_time
        metrics['avg_inference_time_ms'] = (
            metrics['total_inference_time_ms'] / metrics['successful_optimizations']
        )
        
        # Estimate conflicts (simplified)
        conflicts_detected = sum(1 for t in request.trains if t.is_delayed)
        conflicts_resolved = len(resolutions)
        
        logger.info(f"Optimization completed: {num_trains} trains, "
                   f"{len(resolutions)} resolutions, {inference_time:.2f}ms")
        
        return OptimizationResponse(
            success=True,
            resolutions=resolutions,
            total_delay_minutes=total_delay,
            inference_time_ms=inference_time,
            conflicts_detected=conflicts_detected,
            conflicts_resolved=conflicts_resolved,
            timestamp=datetime.now().isoformat()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        metrics['failed_optimizations'] += 1
        logger.error(f"Optimization failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Run Server
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "server:app",
        host="0.0.0.0",
        port=8002,
        reload=True,
        log_level="info"
    )
