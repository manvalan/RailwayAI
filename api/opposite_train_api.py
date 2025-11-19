"""
API JSON per Ottimizzatore Orari Treni Opposti.

Endpoint per integrare l'ottimizzazione con applicazioni esterne.
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from python.scheduling.opposite_train_optimizer import (
    OppositeTrainScheduler,
    TrackSection,
    TrainPath,
    ExistingTrain,
    ScheduleProposal
)

app = FastAPI(
    title="Railway Opposite Train Scheduler API",
    description="Ottimizza orari per treni in senso opposto",
    version="1.0.0"
)


# ============================================================================
# Request/Response Models
# ============================================================================

class TrackSectionModel(BaseModel):
    """Sezione di binario."""
    section_id: int
    start_km: float
    end_km: float
    num_tracks: int = Field(..., ge=1, description="1=singolo, 2+=doppio")
    max_speed_kmh: float
    has_station: bool = False
    station_name: Optional[str] = None
    can_cross: bool = False


class TrainPathModel(BaseModel):
    """Percorso treno."""
    train_id: str
    direction: str = Field(..., pattern="^(forward|backward)$")
    start_km: float
    end_km: float
    avg_speed_kmh: float
    stops: List[List[float]] = Field(default_factory=list, description="[[km, duration_min], ...]")
    priority: int = Field(default=5, ge=1, le=10)


class ExistingTrainModel(BaseModel):
    """Treno esistente."""
    train_id: str
    position_km: float
    velocity_kmh: float
    direction: str


class OptimizeRequest(BaseModel):
    """Richiesta ottimizzazione."""
    track_sections: List[TrackSectionModel]
    train1: TrainPathModel
    train2: TrainPathModel
    time_window_start: str = Field(..., description="ISO format: 2025-11-19T08:00:00")
    time_window_end: str = Field(..., description="ISO format: 2025-11-19T10:00:00")
    frequency_minutes: int = Field(default=60, ge=15, le=240)
    existing_traffic: Optional[List[ExistingTrainModel]] = None


class ScheduleProposalModel(BaseModel):
    """Proposta orario."""
    train1_departure: str
    train2_departure: str
    crossing_point_km: float
    crossing_time: str
    train1_wait_minutes: float
    train2_wait_minutes: float
    total_delay_minutes: float
    conflicts_avoided: int
    confidence: float
    reasoning: str


class OptimizeResponse(BaseModel):
    """Risposta ottimizzazione."""
    success: bool
    proposals: List[ScheduleProposalModel]
    best_proposal: Optional[ScheduleProposalModel] = None
    computation_time_ms: float


# ============================================================================
# Endpoints
# ============================================================================

@app.post("/api/v1/optimize-opposite-trains", response_model=OptimizeResponse)
async def optimize_opposite_trains(request: OptimizeRequest):
    """
    Ottimizza orari per coppia di treni in senso opposto.
    
    Trova gli orari migliori considerando:
    - Topologia rete (singolo/doppio binario)
    - Punti di incrocio ottimali
    - Traffico esistente
    - Minimizzazione ritardi
    
    Esempio richiesta:
    ```json
    {
      "track_sections": [
        {
          "section_id": 1,
          "start_km": 0.0,
          "end_km": 10.0,
          "num_tracks": 1,
          "max_speed_kmh": 120.0,
          "has_station": false,
          "can_cross": false
        },
        {
          "section_id": 2,
          "start_km": 10.0,
          "end_km": 12.0,
          "num_tracks": 2,
          "max_speed_kmh": 80.0,
          "has_station": true,
          "station_name": "Stazione Intermedia",
          "can_cross": true
        }
      ],
      "train1": {
        "train_id": "IC 501",
        "direction": "forward",
        "start_km": 0.0,
        "end_km": 50.0,
        "avg_speed_kmh": 100.0,
        "stops": [[11.0, 2]],
        "priority": 7
      },
      "train2": {
        "train_id": "IC 502",
        "direction": "backward",
        "start_km": 50.0,
        "end_km": 0.0,
        "avg_speed_kmh": 100.0,
        "stops": [[11.0, 2]],
        "priority": 7
      },
      "time_window_start": "2025-11-19T08:00:00",
      "time_window_end": "2025-11-19T10:00:00",
      "frequency_minutes": 60
    }
    ```
    """
    import time
    start_time = time.time()
    
    try:
        # Parse datetime
        time_start = datetime.fromisoformat(request.time_window_start)
        time_end = datetime.fromisoformat(request.time_window_end)
        
        # Converti modelli Pydantic a oggetti interni
        track_sections = [
            TrackSection(
                section_id=s.section_id,
                start_km=s.start_km,
                end_km=s.end_km,
                num_tracks=s.num_tracks,
                max_speed_kmh=s.max_speed_kmh,
                has_station=s.has_station,
                station_name=s.station_name,
                can_cross=s.can_cross
            )
            for s in request.track_sections
        ]
        
        train1 = TrainPath(
            train_id=request.train1.train_id,
            direction=request.train1.direction,
            start_km=request.train1.start_km,
            end_km=request.train1.end_km,
            avg_speed_kmh=request.train1.avg_speed_kmh,
            departure_time=time_start,  # Placeholder
            stops=[(km, dur) for km, dur in request.train1.stops],
            priority=request.train1.priority
        )
        
        train2 = TrainPath(
            train_id=request.train2.train_id,
            direction=request.train2.direction,
            start_km=request.train2.start_km,
            end_km=request.train2.end_km,
            avg_speed_kmh=request.train2.avg_speed_kmh,
            departure_time=time_start,  # Placeholder
            stops=[(km, dur) for km, dur in request.train2.stops],
            priority=request.train2.priority
        )
        
        # Traffico esistente
        existing_traffic = []
        if request.existing_traffic:
            existing_traffic = [
                ExistingTrain(
                    train_id=t.train_id,
                    position_km=t.position_km,
                    velocity_kmh=t.velocity_kmh,
                    direction=t.direction,
                    estimated_times={}
                )
                for t in request.existing_traffic
            ]
        
        # Crea scheduler e ottimizza
        scheduler = OppositeTrainScheduler(track_sections)
        proposals = scheduler.find_optimal_schedule(
            train1,
            train2,
            time_start,
            time_end,
            request.frequency_minutes,
            existing_traffic
        )
        
        # Converti proposte a JSON
        proposal_models = [
            ScheduleProposalModel(
                train1_departure=p.train1_departure.isoformat(),
                train2_departure=p.train2_departure.isoformat(),
                crossing_point_km=p.crossing_point_km,
                crossing_time=p.crossing_time.isoformat(),
                train1_wait_minutes=p.train1_wait_minutes,
                train2_wait_minutes=p.train2_wait_minutes,
                total_delay_minutes=p.total_delay_minutes,
                conflicts_avoided=p.conflicts_avoided,
                confidence=p.confidence,
                reasoning=p.reasoning
            )
            for p in proposals
        ]
        
        computation_time = (time.time() - start_time) * 1000
        
        return OptimizeResponse(
            success=True,
            proposals=proposal_models,
            best_proposal=proposal_models[0] if proposal_models else None,
            computation_time_ms=round(computation_time, 2)
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Errore interno: {str(e)}")


@app.get("/api/v1/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "opposite-train-scheduler",
        "version": "1.0.0"
    }


@app.get("/")
async def root():
    """Root endpoint con info API."""
    return {
        "name": "Railway Opposite Train Scheduler API",
        "version": "1.0.0",
        "endpoints": {
            "optimize": "/api/v1/optimize-opposite-trains",
            "health": "/api/v1/health",
            "docs": "/docs"
        }
    }


if __name__ == "__main__":
    import uvicorn
    print("\n🚂 Starting Opposite Train Scheduler API...")
    print("📖 Documentation: http://localhost:8001/docs")
    uvicorn.run(app, host="0.0.0.0", port=8001)
