"""
API REST per integrazione FDC.

Endpoint conformi a RAILWAY_AI_INTEGRATION_SPECS.md
"""

from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
import asyncio
import time
from fastapi import FastAPI, HTTPException, Depends, status, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from fastapi.security import OAuth2PasswordRequestForm
from python.integration.auth import create_access_token, get_current_user, ACCESS_TOKEN_EXPIRE_MINUTES
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from python.integration.fdc_integration import (
    FDCIntegrationBuilder,
    ConflictType,
    ModificationType
)

app = FastAPI(
    title="RailwayAI FDC Integration API",
    description="API per integrazione con FDC secondo specifiche ufficiali",
    version="2.0.0"
)

# Servire file statici (Dashboard di monitoraggio)
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
                # Connection might be stale
                pass

manager = ConnectionManager()

# Global scheduler instance (for persistent monitoring)
from python.railway_cpp import RailwayScheduler
global_scheduler = RailwayScheduler()

async def event_poller():
    """Polla periodicamente gli eventi dal core C++ e li trasmette."""
    last_log_size = 0
    while True:
        try:
            logs = global_scheduler.get_event_log(100)
            if len(logs) > last_log_size:
                new_logs = logs[last_log_size:]
                for log in new_logs:
                    await manager.broadcast({
                        "type": "log",
                        "content": log,
                        "timestamp": datetime.now().isoformat()
                    })
                last_log_size = len(logs)
                
                # Limitiamo la dimensione del log interno se cresce troppo (>1000 entry)
                if last_log_size > 1000:
                    # Implementazione futura: global_scheduler.clear_old_logs(500)
                    last_log_size = 500 
            
            # Broadcast network state periodically
            state = global_scheduler.get_network_state()
            await manager.broadcast({
                "type": "state_update",
                "train_count": len(state.trains),
                "timestamp": datetime.now().isoformat()
            })
            
        except Exception as e:
            print(f"Poller error: {e}")
            
        await asyncio.sleep(2)

async def log_cleanup_task():
    """Rimuove periodicamente i file di log vecchi per risparmiare spazio."""
    while True:
        try:
            log_file = Path("server.log")
            if log_file.exists() and log_file.stat().st_size > 10 * 1024 * 1024: # 10MB
                # Ruota il log: rinomina il vecchio e ricomincia
                backup = Path(f"server.log.{datetime.now().strftime('%Y%m%d%H%M%S')}")
                log_file.rename(backup)
                print(f"Log rotated to {backup}")
                
                # Rimuovi backup più vecchi di 3 giorni
                current_time = time.time()
                for p in Path(".").glob("server.log.*"):
                    if current_time - p.stat().st_mtime > 3 * 24 * 3600:
                        p.unlink()
                        print(f"Old log removed: {p}")
        except Exception as e:
            print(f"Cleanup error: {e}")
        
        await asyncio.sleep(3600) # Controlla ogni ora

@app.on_event("startup")
async def startup_event():
    # Carica il modello ML all'avvio
    model_path = "models/scheduler_real_world.pt"
    if global_scheduler.load_ml_model(model_path):
        print(f"✅ Modello ML caricato con successo da {model_path}")
    else:
        print(f"⚠️ Caricamento modello ML fallito ({model_path}). Uso euristiche di fallback.")
        
    asyncio.create_task(event_poller())
    asyncio.create_task(log_cleanup_task())

class TrainInfo(BaseModel):
    """Informazioni su un treno."""
    train_id: str
    arrival: Optional[str] = None  # ISO datetime
    departure: Optional[str] = None
    platform: Optional[int] = None
    current_speed_kmh: Optional[float] = None
    priority: int = Field(default=5, ge=1, le=10)


class ConflictInput(BaseModel):
    """Conflitto da risolvere."""
    conflict_type: str  # "platform_conflict", "timing_conflict", etc.
    location: str  # Station ID
    trains: List[TrainInfo]
    severity: str = "medium"
    time_overlap_seconds: Optional[int] = None


class NetworkInfo(BaseModel):
    """Informazioni sulla rete."""
    stations: List[str]
    available_platforms: Dict[str, List[int]]  # station_id -> [platform_numbers]
    max_speeds: Dict[str, float]  # section_id -> max_speed_kmh


class OptimizationRequest(BaseModel):
    """Richiesta di ottimizzazione."""
    conflicts: List[ConflictInput]
    network: NetworkInfo
    preferences: Optional[Dict[str, Any]] = None


# ==================== Endpoints ====================

@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "RailwayAI FDC Integration API",
        "version": "2.0.0",
        "status": "operational",
        "docs": "/docs",
        "spec_compliance": "RAILWAY_AI_INTEGRATION_SPECS.md v1.0"
    }


@app.get("/api/v2/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "railwayai-fdc-integration",
        "timestamp": datetime.now().isoformat()
    }


@app.post("/token")
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    """
    Endpoint per ottenere il token JWT.
    In produzione, verificare le credenziali su DB sicuro.
    """
    # Esempio semplificato: admin/admin
    if form_data.username != "admin" or form_data.password != "admin":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": form_data.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}


@app.post("/api/v2/optimize")
async def optimize_conflicts(
    request: OptimizationRequest,
    current_user: str = Depends(get_current_user)
):
    """
    Ottimizza conflitti e restituisce modifiche dettagliate.
    
    **Conforme a**: RAILWAY_AI_INTEGRATION_SPECS.md
    
    **Esempio richiesta**:
    ```json
    {
      "conflicts": [
        {
          "conflict_type": "platform_conflict",
          "location": "MONZA",
          "trains": [
            {
              "train_id": "IC101",
              "arrival": "2025-11-19T08:08:00",
              "departure": "2025-11-19T08:10:00",
              "platform": 1
            },
            {
              "train_id": "R203",
              "arrival": "2025-11-19T08:09:00",
              "departure": "2025-11-19T08:11:00",
              "platform": 1
            }
          ],
          "severity": "high",
          "time_overlap_seconds": 60
        }
      ],
      "network": {
        "stations": ["MILANO_CENTRALE", "MONZA", "COMO"],
        "available_platforms": {
          "MONZA": [1, 2, 3]
        },
        "max_speeds": {
          "MILANO_MONZA": 140.0
        }
      }
    }
    ```
    
    **Risposta**: Oggetto FDCResponse con modifiche dettagliate.
    """
    try:
        # Analizza conflitti
        builder = FDCIntegrationBuilder()
        builder.set_ml_confidence(0.90)
        
        for conflict in request.conflicts:
            # Registra conflitto
            conf_type = ConflictType.PLATFORM_CONFLICT  # Default
            if "platform" in conflict.conflict_type.lower():
                conf_type = ConflictType.PLATFORM_CONFLICT
            elif "timing" in conflict.conflict_type.lower():
                conf_type = ConflictType.TIMING_CONFLICT
            elif "speed" in conflict.conflict_type.lower():
                conf_type = ConflictType.SPEED_CONFLICT
            elif "capacity" in conflict.conflict_type.lower():
                conf_type = ConflictType.CAPACITY_CONFLICT
            
            builder.add_conflict(
                conflict_type=conf_type,
                location=conflict.location,
                trains=[t.train_id for t in conflict.trains],
                severity=conflict.severity,
                time_overlap_seconds=conflict.time_overlap_seconds
            )
            
            # Strategia di risoluzione
            if conf_type == ConflictType.PLATFORM_CONFLICT:
                # Prova cambio binario se disponibile
                station = conflict.location
                if station in request.network.available_platforms:
                    available = request.network.available_platforms[station]
                    used_platforms = {t.platform for t in conflict.trains if t.platform}
                    
                    # Trova binario libero
                    free_platforms = [p for p in available if p not in used_platforms]
                    
                    if free_platforms:
                        # Cambia binario al treno con priorità minore
                        train_to_move = min(conflict.trains, key=lambda t: t.priority)
                        
                        builder.add_platform_change(
                            train_id=train_to_move.train_id,
                            station=station,
                            new_platform=free_platforms[0],
                            original_platform=train_to_move.platform,
                            affected_stations=[station],
                            reason=f"Cambio binario risolve conflitto a {station}",
                            confidence=0.95
                        )
                    else:
                        # Nessun binario libero → ritarda
                        train_to_delay = min(conflict.trains, key=lambda t: t.priority)
                        builder.add_departure_delay(
                            train_id=train_to_delay.train_id,
                            station="ORIGIN",  # Da determinare
                            delay_seconds=120,
                            affected_stations=[station],
                            reason="Ritardo per mancanza binari liberi",
                            confidence=0.80
                        )
            
            elif conf_type == ConflictType.TIMING_CONFLICT:
                # Riduci velocità del treno più veloce
                fastest_train = max(
                    conflict.trains,
                    key=lambda t: t.current_speed_kmh or 0
                )
                
                if fastest_train.current_speed_kmh:
                    new_speed = fastest_train.current_speed_kmh * 0.8
                    
                    builder.add_speed_modification(
                        train_id=fastest_train.train_id,
                        from_station="PREV_STATION",  # Da determinare
                        to_station=conflict.location,
                        new_speed_kmh=new_speed,
                        original_speed_kmh=fastest_train.current_speed_kmh,
                        time_increase_seconds=int(
                            (fastest_train.current_speed_kmh - new_speed) / 
                            fastest_train.current_speed_kmh * 600
                        ),
                        affected_stations=[conflict.location],
                        reason=f"Riduzione velocità per evitare conflitto a {conflict.location}",
                        confidence=0.88
                    )
        
        # Costruisci risposta
        response = builder.build_success()
        return response.to_dict()
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class SimpleOptimizationRequest(BaseModel):
    """Richiesta semplificata."""
    train_id: str
    origin_station: str
    delay_seconds: int
    affected_stations: List[str]
    reason: str
    confidence: float = 0.85


@app.post("/api/v2/optimize/simple")
async def optimize_simple(
    request: SimpleOptimizationRequest,
    current_user: str = Depends(get_current_user)
):
    """
    Endpoint semplificato per ottimizzazione minimale.
    
    **Usa quando**: Non hai informazioni dettagliate sui conflitti.
    
    **Esempio**:
    ```
    POST /api/v2/optimize/simple
    {
      "train_id": "IC101",
      "origin_station": "MILANO_CENTRALE",
      "delay_seconds": 180,
      "affected_stations": ["MILANO_CENTRALE", "MONZA", "COMO"],
      "reason": "Ritardo per evitare conflitto",
      "confidence": 0.85
    }
    ```
    """
    from python.integration.fdc_integration import create_minimal_fdc_response
    
    response = create_minimal_fdc_response(
        train_id=request.train_id,
        origin_station=request.origin_station,
        delay_seconds=request.delay_seconds,
        affected_stations=request.affected_stations,
        reason=request.reason,
        confidence=request.confidence
    )
    
    return response


class ValidationRequest(BaseModel):
    """Richiesta di validazione."""
    modifications: List[Dict[str, Any]]


@app.post("/api/v2/validate")
async def validate_modifications(
    request: ValidationRequest,
    current_user: str = Depends(get_current_user)
):
    """
    Valida modifiche prima di applicarle.
    
    **Restituisce**: Lista di errori di validazione o successo.
    """
    modifications = request.modifications
    errors = []
    
    for i, mod in enumerate(modifications):
        # Valida campi obbligatori
        required = ["train_id", "modification_type", "section", "parameters", "impact"]
        missing = [f for f in required if f not in mod]
        
        if missing:
            errors.append({
                "modification_index": i,
                "train_id": mod.get("train_id", "unknown"),
                "error": f"Campi mancanti: {', '.join(missing)}"
            })
        
        # Valida modification_type
        mod_type = mod.get("modification_type")
        valid_types = [t.value for t in ModificationType]
        if mod_type and mod_type not in valid_types:
            errors.append({
                "modification_index": i,
                "train_id": mod.get("train_id"),
                "error": f"modification_type '{mod_type}' non valido. Validi: {valid_types}"
            })
    
    if errors:
        return {
            "valid": False,
            "errors": errors
        }
    else:
        return {
            "valid": True,
            "message": f"Tutte le {len(modifications)} modifiche sono valide"
        }


@app.websocket("/ws/monitoring")
async def websocket_endpoint(websocket: WebSocket):
    """
    Endpoint WebSocket per il monitoraggio in tempo reale.
    """
    await manager.connect(websocket)
    try:
        while True:
            # Keep connection alive and receive optional messages
            data = await websocket.receive_text()
            # Handle client commands if needed
    except WebSocketDisconnect:
        manager.disconnect(websocket)


@app.get("/api/v2/modification-types")
async def get_modification_types():
    """
    Restituisce tipi di modifiche supportate.
    
    **Utile per**: Scoperta delle capacità API.
    """
    return {
        "modification_types": [
            {
                "type": t.value,
                "description": _get_modification_description(t)
            }
            for t in ModificationType
        ]
    }


def _get_modification_description(mod_type: ModificationType) -> str:
    """Descrizione tipo modifica."""
    descriptions = {
        ModificationType.SPEED_REDUCTION: "Riduce velocità su una tratta",
        ModificationType.SPEED_INCREASE: "Aumenta velocità su una tratta",
        ModificationType.PLATFORM_CHANGE: "Cambia binario in stazione",
        ModificationType.DWELL_TIME_INCREASE: "Aumenta tempo di sosta",
        ModificationType.DWELL_TIME_DECREASE: "Riduce tempo di sosta",
        ModificationType.DEPARTURE_DELAY: "Ritarda partenza",
        ModificationType.DEPARTURE_ADVANCE: "Anticipa partenza",
        ModificationType.STOP_SKIP: "Salta fermata",
        ModificationType.ROUTE_CHANGE: "Cambia percorso"
    }
    return descriptions.get(mod_type, "Tipo sconosciuto")


if __name__ == '__main__':
    import uvicorn
    
    print("\n🚂 Starting RailwayAI FDC Integration API...")
    print("📖 Documentation: http://localhost:8002/docs")
    print("📋 Spec compliance: RAILWAY_AI_INTEGRATION_SPECS.md v1.0")
    print("🔌 FDC Integration: READY\n")
    
    uvicorn.run(app, host="0.0.0.0", port=8002)
