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
from python.integration.user_service import UserService
from fastapi.security import OAuth2PasswordRequestForm

from python.models.scheduler_network import SchedulerNetwork
from python.scheduling.route_planner import RoutePlanner
from python.scheduling.temporal_simulator import TemporalSimulator
from python.scheduling.network_analyzer import NetworkAnalyzer
from python.scheduling.schedule_optimizer import ScheduleOptimizer
from contextlib import asynccontextmanager
from python.scheduling.conflict_resolver import ConflictResolver


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup logic
    logger.info("Starting Railway AI Scheduler API v2.0.0...")
    load_model()
    poller_task = asyncio.create_task(event_poller())
    yield
    # Shutdown logic
    poller_task.cancel()
    try:
        await poller_task
    except asyncio.CancelledError:
        pass
    logger.info("Server shutting down...")

# Initialize FastAPI
app = FastAPI(
    title="Railway AI Scheduler API",
    description="ML-powered train schedule optimization",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
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

# Note: on_event is deprecated. Using lifespan instead.

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
    user = UserService.get_user(form_data.username)
    if user and UserService.verify_password(form_data.password, user['hashed_password']):
        if not user.get('is_active', True):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, 
                detail="Account is inactive. Please contact administrator."
            )
        access_token = create_access_token(data={"sub": form_data.username})
        return {
            "access_token": access_token, 
            "token_type": "bearer",
            "message": "Login effettuato con successo via database."
        }
    raise HTTPException(status_code=401, detail="Incorrect username or password")

@app.post("/api/v1/generate-key")
async def release_api_key(current_user: str = Depends(get_current_user)):
    """Rilascia una API Key permanente per l'utente autenticato salvandola nel DB."""
    key = UserService.generate_api_key(current_user)
    if not key:
        raise HTTPException(status_code=500, detail="Failed to generate API Key")
    return {
        "api_key": key,
        "instructions": "Includi questa chiave nell'header 'X-API-Key' per ogni richiesta futura.",
        "notice": "Questa chiave è ora persistente nel database."
    }

# ============================================================================
# Request/Response Models
# ============================================================================

class UserRegistrationRequest(BaseModel):
    """Request for new user registration"""
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6)

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
route_planner = None
temporal_simulator = None
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
    
    # New fields for route planning
    origin_station: Optional[int] = Field(None, description="Origin station ID")
    scheduled_departure_time: Optional[str] = Field(None, description="Scheduled departure time (HH:MM:SS)")
    planned_route: Optional[List[int]] = Field(None, description="Planned sequence of track IDs")
    current_route_index: int = Field(0, description="Current position in planned route")


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
    max_iterations: int = Field(100, ge=1, le=1000, description="Max simulation horizon (minutes)")
    ga_max_iterations: Optional[int] = Field(200, ge=10, le=1000, description="Max GA iterations")
    ga_population_size: Optional[int] = Field(80, ge=10, le=500, description="GA population size")


@app.post("/api/v1/register", status_code=status.HTTP_201_CREATED)
async def register_user(
    request: UserRegistrationRequest,
    current_user: str = Depends(get_current_user)
):
    """
    Registra un nuovo utente. 
    """
    if current_user != "admin":
        raise HTTPException(status_code=403, detail="Only 'admin' can register new users")
        
    if UserService.get_user(request.username):
        raise HTTPException(status_code=400, detail="Username already exists")
        
    success = UserService.create_user(request.username, request.password)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to create user")
        
    return {"message": f"User {request.username} created successfully"}

class TimeWindow(BaseModel):
    """Time window for schedule optimization"""
    start: str = Field(..., description="Start time HH:MM:SS")
    end: str = Field(..., description="End time HH:MM:SS")


class OptimizationParams(BaseModel):
    """Parameters for genetic algorithm optimization"""
    max_iterations: int = Field(1000, ge=100, le=10000, description="Maximum iterations")
    population_size: int = Field(50, ge=10, le=200, description="Population size")
    mutation_rate: float = Field(0.1, ge=0.0, le=1.0, description="Mutation rate")


class ScheduleSuggestionRequest(BaseModel):
    """Request for schedule suggestion with capacity planning"""
    trains: List[Train] = Field(..., description="Trains to schedule (without departure times)")
    tracks: List[Track] = Field(..., description="Track configuration")
    stations: List[Station] = Field(..., description="Station configuration")
    time_window: TimeWindow = Field(..., description="Time window for scheduling")
    target_capacity_utilization: float = Field(0.66, ge=0.1, le=1.0, description="Target capacity utilization")
    optimization_params: OptimizationParams = Field(default_factory=OptimizationParams)


class SuggestedTrain(BaseModel):
    """Train with suggested departure time"""
    train_id: int
    suggested_departure_time: str
    estimated_arrival_time: Optional[str] = None
    route: List[int]
    conflicts: int
    dwell_delays: List[float] = []


class NetworkMetrics(BaseModel):
    """Network-wide capacity metrics"""
    average_capacity_utilization: float
    peak_capacity_utilization: float
    total_conflicts: int
    temporal_distribution_score: float


class TrackUtilization(BaseModel):
    """Utilization metrics for a single track"""
    track_id: int
    utilization: float
    is_bottleneck: bool
    theoretical_capacity: float
    demand: int


class ScheduleSuggestionResponse(BaseModel):
    """Response with suggested schedule"""
    success: bool
    suggested_schedule: List[SuggestedTrain]
    network_metrics: NetworkMetrics
    track_utilization: List[TrackUtilization]
    optimization_info: Dict
    timestamp: str


class Resolution(BaseModel):
    """Resolution action for a train"""
    train_id: int
    time_adjustment_min: float
    track_assignment: Optional[int] = None
    confidence: float = Field(..., ge=0.0, le=1.0)
    dwell_delays: List[float] = []


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

def load_model(checkpoint_path: Optional[str] = None):
    """Load the trained ML model"""
    global model, model_config, metrics
    
    try:
        # Priorità 1: Variabile d'ambiente MODEL_PATH
        env_path = os.getenv("MODEL_PATH")
        if env_path:
            checkpoint_path = env_path
            logger.info(f"Using MODEL_PATH from environment: {checkpoint_path}")
        
        # Priorità 2: Fallback ai percorsi predefiniti se non specificato
        if not checkpoint_path:
            # Prova prima il nuovo path in api/models/
            checkpoint_path = 'api/models/scheduler_supervised_best.pth'
            if not os.path.exists(checkpoint_path):
                # Fallback per compatibilità
                checkpoint_path = 'models/scheduler_real_world.pth'
            
        logger.info(f"Loading model from {checkpoint_path}")
        try:
            # Tenta di caricare come TorchScript prima
            model = torch.jit.load(checkpoint_path, map_location='cpu')
            logger.info("Detected TorchScript model.")
            # Default config for JIT models
            model_config = {
                'input_dim': 256, 'hidden_dim': 512, 
                'num_trains': 50, 'num_tracks': 50, 'num_stations': 30
            }
        except Exception:
            # Fallback a caricamento state_dict (checkpoint classico)
            checkpoint = torch.load(checkpoint_path, map_location='cpu')
            if 'model_state_dict' in checkpoint:
                model_config = checkpoint['config']
                model = SchedulerNetwork(
                    input_dim=model_config['input_dim'],
                    hidden_dim=model_config['hidden_dim'],
                    num_trains=model_config['num_trains'],
                    num_tracks=model_config['num_tracks'],
                    num_stations=model_config['num_stations']
                )
                model.load_state_dict(checkpoint['model_state_dict'])
            else:
                raise ValueError("Unsupported model format")
        
        model.eval()
        metrics['model_loaded_at'] = datetime.now().isoformat()
        
        logger.info(f"Model loaded successfully from {checkpoint_path}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to load model: {e}")
        return False




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


@app.post("/api/v1/optimize_scheduled", response_model=OptimizationResponse, tags=["Optimization"])
async def optimize_scheduled_trains(
    request: OptimizationRequest,
    background_tasks: BackgroundTasks,
    current_user: str = Depends(get_current_user)
):
    """
    Optimize train schedule with route planning and temporal simulation.
    
    Supports:
    - Scheduled departure times
    - Automatic route planning between origin and destination
    - Future conflict detection over time horizon
    - Optimal departure time adjustments
    """
    global route_planner, temporal_simulator
    
    start_time = time.time()
    metrics['total_requests'] += 1
    
    if model is None:
        metrics['failed_optimizations'] += 1
        raise HTTPException(status_code=503, detail="Model not loaded")
    
    try:
        # ALWAYS Initialize route planner and simulator if tracks/stations are provided
        # to ensure we use the current network configuration from the request
        if request.tracks and request.stations:
            logger.info(f"Initializing planners with {len(request.tracks)} tracks and {len(request.stations)} stations")
            route_planner = RoutePlanner(
                [t.dict() for t in request.tracks],
                [s.dict() for s in request.stations]
            )
            temporal_simulator = TemporalSimulator(
                {t.id: t.dict() for t in request.tracks}
            )
        
        if route_planner is None or temporal_simulator is None:
            raise HTTPException(
                status_code=400,
                detail="Route planner not initialized. Please provide tracks and stations."
            )
        
        # Plan routes for trains that need it
        trains_with_routes = []
        for train in request.trains:
            train_dict = train.dict()
            
            # Auto-plan route if origin and destination provided but no planned_route
            if train.planned_route is None and train.origin_station is not None:
                logger.info(f"Planning route for train {train.id} from station {train.origin_station} "
                           f"to {train.destination_station}")
                
                route_plan = route_planner.plan_route(
                    train.origin_station,
                    train.destination_station,
                    avg_speed_kmh=train.velocity_kmh if train.velocity_kmh > 0 else 120.0
                )
                
                if route_plan:
                    train_dict['planned_route'] = route_plan['track_ids']
                    logger.info(f"Route planned for train {train.id}: {len(route_plan['track_ids'])} tracks, "
                               f"{route_plan['total_distance_km']:.1f} km, "
                               f"{route_plan['total_time_minutes']:.1f} min")
                else:
                    logger.warning(f"Could not plan route for train {train.id} from {train.origin_station} "
                                 f"to {train.destination_station}")
            
            trains_with_routes.append(train_dict)
        
        # Detect future conflicts using temporal simulation
        time_horizon = request.max_iterations  # Use max_iterations as time horizon in minutes
        logger.info(f"Detecting future conflicts over {time_horizon} minute horizon")
        
        future_conflicts = temporal_simulator.detect_future_conflicts(
            trains_with_routes,
            time_horizon_minutes=float(time_horizon),
            time_step_minutes=1.0
        )
        
        
        # Use genetic algorithm to resolve conflicts
        if future_conflicts:
            logger.info(f"Resolving {len(future_conflicts)} conflicts using genetic algorithm")
            
            # Initialize conflict resolver
            conflict_resolver = ConflictResolver(temporal_simulator, route_planner)
            
            # Resolve conflicts
            resolution_result = conflict_resolver.resolve_conflicts(
                trains_with_routes,
                time_horizon_minutes=time_horizon,
                max_iterations=getattr(request, 'ga_max_iterations', None) or 200,
                population_size=getattr(request, 'ga_population_size', None) or 80
            )
            
            resolutions = []
            for res in resolution_result['resolutions']:
                # Find track where conflict occurred
                track_id = None
                for conflict in future_conflicts:
                    if conflict['train1_id'] == res['train_id'] or conflict['train2_id'] == res['train_id']:
                        track_id = conflict['track_id']
                        break
                
                logger.info(f"Adding resolution for train {res['train_id']}: dep_delay={res['time_adjustment_min']:.1f}m, "
                            f"dwell_delays={res.get('dwell_delays', [])}")
                
                resolutions.append(Resolution(
                    train_id=res['train_id'],
                    time_adjustment_min=res['time_adjustment_min'],
                    track_assignment=track_id,
                    confidence=res['confidence'],
                    dwell_delays=res.get('dwell_delays', [])
                ))
            
            total_delay = resolution_result['total_delay']
            conflicts_resolved = resolution_result['conflicts_resolved']
            
            logger.info(f"Genetic algorithm completed: {conflicts_resolved} conflicts resolved, "
                       f"total delay={total_delay:.1f} min")
        else:
            resolutions = []
            total_delay = 0.0
            conflicts_resolved = 0

        
        # Calculate metrics
        inference_time = (time.time() - start_time) * 1000.0
        total_delay = sum(r.time_adjustment_min for r in resolutions)
        
        # Update global metrics
        metrics['successful_optimizations'] += 1
        metrics['total_inference_time_ms'] += inference_time
        metrics['avg_inference_time_ms'] = (
            metrics['total_inference_time_ms'] / metrics['successful_optimizations']
        )
        
        logger.info(f"Scheduled optimization completed: {len(request.trains)} trains, "
                   f"{len(future_conflicts)} conflicts detected, {len(resolutions)} resolutions, "
                   f"{inference_time:.2f}ms")
        
        return OptimizationResponse(
            success=True,
            resolutions=resolutions,
            total_delay_minutes=total_delay,
            inference_time_ms=inference_time,
            conflicts_detected=len(future_conflicts),
            conflicts_resolved=conflicts_resolved,
            timestamp=datetime.now().isoformat()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        metrics['failed_optimizations'] += 1
        logger.error(f"Scheduled optimization failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/suggest_schedule", response_model=ScheduleSuggestionResponse, tags=["Optimization"])
async def suggest_schedule(
    request: ScheduleSuggestionRequest,
    background_tasks: BackgroundTasks,
    current_user: str = Depends(get_current_user)
):
    """Suggest optimal train schedule to achieve target capacity utilization."""
    global route_planner, temporal_simulator
    
    start_time = time.time()
    metrics['total_requests'] += 1
    
    try:
        if route_planner is None or temporal_simulator is None:
            route_planner = RoutePlanner(
                [t.dict() for t in request.tracks],
                [s.dict() for s in request.stations]
            )
            temporal_simulator = TemporalSimulator({t.id: t.dict() for t in request.tracks})
        
        analyzer = NetworkAnalyzer([t.dict() for t in request.tracks], [s.dict() for s in request.stations])
        
        start_h, start_m, start_s = map(int, request.time_window.start.split(':'))
        end_h, end_m, end_s = map(int, request.time_window.end.split(':'))
        window_hours = ((end_h * 60 + end_m) - (start_h * 60 + start_m)) / 60.0
        
        network_metrics = analyzer.analyze_capacity([t.dict() for t in request.trains], window_hours)
        bottlenecks = analyzer.identify_bottlenecks(network_metrics)
        
        trains_with_routes = []
        for train in request.trains:
            train_dict = train.dict()
            if train.origin_station and train.destination_station:
                route_plan = route_planner.plan_route(
                    train.origin_station, train.destination_station,
                    avg_speed_kmh=train.velocity_kmh if train.velocity_kmh > 0 else 120.0
                )
                if route_plan:
                    train_dict['planned_route'] = route_plan['track_ids']
            trains_with_routes.append(train_dict)
        
        optimizer = ScheduleOptimizer(
            network_metrics, trains_with_routes, request.time_window.dict(),
            request.target_capacity_utilization, route_planner, temporal_simulator
        )
        
        result = optimizer.optimize(
            request.optimization_params.max_iterations,
            request.optimization_params.population_size,
            request.optimization_params.mutation_rate
        )
        
        suggested_trains = [
            SuggestedTrain(
                train_id=t['id'],
                suggested_departure_time=t['scheduled_departure_time'],
                route=t.get('planned_route', []),
                conflicts=0
            ) for t in result['schedule']
        ]
        
        track_utilization = [
            TrackUtilization(
                track_id=tid, utilization=m['utilization'],
                is_bottleneck=m['is_bottleneck'],
                theoretical_capacity=m['theoretical_capacity'],
                demand=m['demand']
            ) for tid, m in network_metrics.items()
        ]
        
        network_stats = analyzer.calculate_network_utilization(network_metrics)
        computation_time = (time.time() - start_time) * 1000.0
        metrics['successful_optimizations'] += 1
        
        return ScheduleSuggestionResponse(
            success=True,
            suggested_schedule=suggested_trains,
            network_metrics=NetworkMetrics(
                average_capacity_utilization=result['metrics']['average_capacity_utilization'],
                peak_capacity_utilization=network_stats['max'],
                total_conflicts=result['metrics']['total_conflicts'],
                temporal_distribution_score=result['metrics']['temporal_distribution_score']
            ),
            track_utilization=track_utilization,
            optimization_info={
                'iterations': result['iterations'],
                'convergence_score': result['convergence'],
                'computation_time_ms': computation_time,
                'bottlenecks_identified': len(bottlenecks)
            },
            timestamp=datetime.now().isoformat()
        )
    except HTTPException:
        raise
    except Exception as e:
        metrics['failed_optimizations'] += 1
        logger.error(f"Schedule suggestion failed: {e}", exc_info=True)
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
