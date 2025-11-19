"""
API REST per integrazione FDC.

Endpoint conformi a RAILWAY_AI_INTEGRATION_SPECS.md
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
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


# ==================== Pydantic Models ====================

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


@app.post("/api/v2/optimize")
async def optimize_conflicts(request: OptimizationRequest):
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
async def optimize_simple(request: SimpleOptimizationRequest):
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
async def validate_modifications(request: ValidationRequest):
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
