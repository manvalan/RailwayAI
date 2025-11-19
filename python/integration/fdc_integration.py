"""
FDC Integration Module for RailwayAI

Questo modulo fornisce il formato JSON enhanced richiesto da FDC
secondo le specifiche in RAILWAY_AI_INTEGRATION_SPECS.md
"""

from typing import List, Dict, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from enum import Enum


class ModificationType(Enum):
    """Tipi di modifiche supportate."""
    SPEED_REDUCTION = "speed_reduction"
    SPEED_INCREASE = "speed_increase"
    PLATFORM_CHANGE = "platform_change"
    DWELL_TIME_INCREASE = "dwell_time_increase"
    DWELL_TIME_DECREASE = "dwell_time_decrease"
    DEPARTURE_DELAY = "departure_delay"
    DEPARTURE_ADVANCE = "departure_advance"
    STOP_SKIP = "stop_skip"
    ROUTE_CHANGE = "route_change"


class ConflictType(Enum):
    """Tipi di conflitti rilevabili."""
    PLATFORM_CONFLICT = "platform_conflict"
    SPEED_CONFLICT = "speed_conflict"
    TIMING_CONFLICT = "timing_conflict"
    CAPACITY_CONFLICT = "capacity_conflict"


@dataclass
class Section:
    """Sezione di rete interessata dalla modifica."""
    station: Optional[str] = None  # Per modifiche a singola stazione
    from_station: Optional[str] = None  # Per modifiche su tratta
    to_station: Optional[str] = None


@dataclass
class SpeedParameters:
    """Parametri per modifiche di velocità."""
    new_speed_kmh: float
    original_speed_kmh: Optional[float] = None


@dataclass
class PlatformParameters:
    """Parametri per cambio binario."""
    new_platform: int
    original_platform: Optional[int] = None


@dataclass
class DwellTimeParameters:
    """Parametri per modifica tempo di sosta."""
    additional_seconds: int  # Può essere negativo
    original_dwell_seconds: Optional[int] = None


@dataclass
class DelayParameters:
    """Parametri per ritardo/anticipo."""
    delay_seconds: int  # Negativo = anticipo


@dataclass
class RouteParameters:
    """Parametri per cambio percorso."""
    new_route: List[str]
    original_route: Optional[List[str]] = None


@dataclass
class StopSkipParameters:
    """Parametri per salto fermata."""
    reason: str


@dataclass
class Impact:
    """Impatto della modifica."""
    time_increase_seconds: int
    affected_stations: List[str]
    passenger_impact_score: Optional[float] = None  # 0.0-1.0


@dataclass
class Modification:
    """Singola modifica a un treno."""
    train_id: str
    modification_type: str  # ModificationType as string
    section: Dict[str, Any]  # Section serializzata
    parameters: Dict[str, Any]  # Parameters specifici serializzati
    impact: Dict[str, Any]  # Impact serializzato
    reason: str
    confidence: float  # 0.0-1.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Converte in dizionario per JSON."""
        return {
            "train_id": self.train_id,
            "modification_type": self.modification_type,
            "section": self.section,
            "parameters": self.parameters,
            "impact": self.impact,
            "reason": self.reason,
            "confidence": self.confidence
        }


@dataclass
class Alternative:
    """Soluzione alternativa."""
    description: str
    total_impact_minutes: float
    confidence: float
    modifications: List[Modification]
    
    def to_dict(self) -> Dict[str, Any]:
        """Converte in dizionario per JSON."""
        return {
            "description": self.description,
            "total_impact_minutes": self.total_impact_minutes,
            "confidence": self.confidence,
            "modifications": [m.to_dict() for m in self.modifications]
        }


@dataclass
class ConflictDetail:
    """Dettaglio di un conflitto."""
    type: str  # ConflictType as string
    location: str
    trains: List[str]
    severity: str  # "low", "medium", "high"
    time_overlap_seconds: Optional[int] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Converte in dizionario per JSON."""
        result = {
            "type": self.type,
            "location": self.location,
            "trains": self.trains,
            "severity": self.severity
        }
        if self.time_overlap_seconds is not None:
            result["time_overlap_seconds"] = self.time_overlap_seconds
        return result


@dataclass
class UnresolvedConflict:
    """Conflitto non risolto."""
    type: str
    description: str
    affected_trains: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.type,
            "description": self.description,
            "affected_trains": self.affected_trains
        }


@dataclass
class ConflictAnalysis:
    """Analisi dei conflitti."""
    original_conflicts: List[ConflictDetail]
    resolved_conflicts: int
    remaining_conflicts: int
    unresolved_details: Optional[List[UnresolvedConflict]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Converte in dizionario per JSON."""
        result = {
            "original_conflicts": [c.to_dict() for c in self.original_conflicts],
            "resolved_conflicts": self.resolved_conflicts,
            "remaining_conflicts": self.remaining_conflicts
        }
        if self.unresolved_details:
            result["unresolved_details"] = [u.to_dict() for u in self.unresolved_details]
        return result


@dataclass
class FDCResponse:
    """Risposta completa per FDC secondo specifiche."""
    success: bool
    modifications: List[Modification]
    total_impact_minutes: float
    ml_confidence: float
    optimization_type: str = "multi_train_coordination"
    alternatives: Optional[List[Alternative]] = None
    conflict_analysis: Optional[ConflictAnalysis] = None
    error_message: Optional[str] = None
    error_code: Optional[str] = None
    suggestions: Optional[List[str]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Converte in dizionario per JSON."""
        result = {
            "success": self.success,
            "optimization_type": self.optimization_type,
            "total_impact_minutes": self.total_impact_minutes,
            "ml_confidence": self.ml_confidence,
            "modifications": [m.to_dict() for m in self.modifications]
        }
        
        if self.alternatives:
            result["alternatives"] = [a.to_dict() for a in self.alternatives]
        
        if self.conflict_analysis:
            result["conflict_analysis"] = self.conflict_analysis.to_dict()
        
        if self.error_message:
            result["error_message"] = self.error_message
        
        if self.error_code:
            result["error_code"] = self.error_code
        
        if self.suggestions:
            result["suggestions"] = self.suggestions
        
        return result


class FDCIntegrationBuilder:
    """Builder per creare risposte FDC-compliant."""
    
    def __init__(self):
        self.modifications: List[Modification] = []
        self.alternatives: List[Alternative] = []
        self.original_conflicts: List[ConflictDetail] = []
        self.unresolved_conflicts: List[UnresolvedConflict] = []
        self.ml_confidence: float = 0.0
        self.optimization_type: str = "multi_train_coordination"
    
    def add_speed_modification(
        self,
        train_id: str,
        from_station: str,
        to_station: str,
        new_speed_kmh: float,
        original_speed_kmh: float,
        time_increase_seconds: int,
        affected_stations: List[str],
        reason: str,
        confidence: float = 0.9
    ) -> 'FDCIntegrationBuilder':
        """Aggiunge modifica velocità."""
        mod = Modification(
            train_id=train_id,
            modification_type=ModificationType.SPEED_REDUCTION.value if new_speed_kmh < original_speed_kmh else ModificationType.SPEED_INCREASE.value,
            section={"from_station": from_station, "to_station": to_station},
            parameters={
                "new_speed_kmh": new_speed_kmh,
                "original_speed_kmh": original_speed_kmh
            },
            impact={
                "time_increase_seconds": time_increase_seconds,
                "affected_stations": affected_stations
            },
            reason=reason,
            confidence=confidence
        )
        self.modifications.append(mod)
        return self
    
    def add_platform_change(
        self,
        train_id: str,
        station: str,
        new_platform: int,
        original_platform: int,
        affected_stations: List[str],
        reason: str,
        confidence: float = 0.95
    ) -> 'FDCIntegrationBuilder':
        """Aggiunge cambio binario."""
        mod = Modification(
            train_id=train_id,
            modification_type=ModificationType.PLATFORM_CHANGE.value,
            section={"station": station},
            parameters={
                "new_platform": new_platform,
                "original_platform": original_platform
            },
            impact={
                "time_increase_seconds": 0,  # Cambio binario di solito non aggiunge ritardo
                "affected_stations": affected_stations
            },
            reason=reason,
            confidence=confidence
        )
        self.modifications.append(mod)
        return self
    
    def add_dwell_time_change(
        self,
        train_id: str,
        station: str,
        additional_seconds: int,
        original_dwell_seconds: int,
        affected_stations: List[str],
        reason: str,
        confidence: float = 0.88
    ) -> 'FDCIntegrationBuilder':
        """Aggiunge modifica tempo di sosta."""
        mod_type = ModificationType.DWELL_TIME_INCREASE if additional_seconds > 0 else ModificationType.DWELL_TIME_DECREASE
        mod = Modification(
            train_id=train_id,
            modification_type=mod_type.value,
            section={"station": station},
            parameters={
                "additional_seconds": additional_seconds,
                "original_dwell_seconds": original_dwell_seconds
            },
            impact={
                "time_increase_seconds": abs(additional_seconds),
                "affected_stations": affected_stations
            },
            reason=reason,
            confidence=confidence
        )
        self.modifications.append(mod)
        return self
    
    def add_departure_delay(
        self,
        train_id: str,
        station: str,
        delay_seconds: int,
        affected_stations: List[str],
        reason: str,
        confidence: float = 0.85
    ) -> 'FDCIntegrationBuilder':
        """Aggiunge ritardo/anticipo partenza."""
        mod_type = ModificationType.DEPARTURE_DELAY if delay_seconds > 0 else ModificationType.DEPARTURE_ADVANCE
        mod = Modification(
            train_id=train_id,
            modification_type=mod_type.value,
            section={"station": station},
            parameters={"delay_seconds": delay_seconds},
            impact={
                "time_increase_seconds": abs(delay_seconds),
                "affected_stations": affected_stations
            },
            reason=reason,
            confidence=confidence
        )
        self.modifications.append(mod)
        return self
    
    def add_conflict(
        self,
        conflict_type: ConflictType,
        location: str,
        trains: List[str],
        severity: str = "medium",
        time_overlap_seconds: Optional[int] = None
    ) -> 'FDCIntegrationBuilder':
        """Aggiunge conflitto originale."""
        conflict = ConflictDetail(
            type=conflict_type.value,
            location=location,
            trains=trains,
            severity=severity,
            time_overlap_seconds=time_overlap_seconds
        )
        self.original_conflicts.append(conflict)
        return self
    
    def add_alternative(
        self,
        description: str,
        modifications: List[Modification],
        confidence: float
    ) -> 'FDCIntegrationBuilder':
        """Aggiunge soluzione alternativa."""
        total_impact = sum(m.impact["time_increase_seconds"] for m in modifications) / 60.0
        alt = Alternative(
            description=description,
            total_impact_minutes=total_impact,
            confidence=confidence,
            modifications=modifications
        )
        self.alternatives.append(alt)
        return self
    
    def set_ml_confidence(self, confidence: float) -> 'FDCIntegrationBuilder':
        """Imposta confidence globale ML."""
        self.ml_confidence = confidence
        return self
    
    def set_optimization_type(self, opt_type: str) -> 'FDCIntegrationBuilder':
        """Imposta tipo di ottimizzazione."""
        self.optimization_type = opt_type
        return self
    
    def build_success(self) -> FDCResponse:
        """Costruisce risposta di successo."""
        total_impact = sum(m.impact["time_increase_seconds"] for m in self.modifications) / 60.0
        resolved = len([c for c in self.original_conflicts])
        
        conflict_analysis = ConflictAnalysis(
            original_conflicts=self.original_conflicts,
            resolved_conflicts=resolved,
            remaining_conflicts=0
        )
        
        return FDCResponse(
            success=True,
            modifications=self.modifications,
            total_impact_minutes=total_impact,
            ml_confidence=self.ml_confidence,
            optimization_type=self.optimization_type,
            alternatives=self.alternatives if self.alternatives else None,
            conflict_analysis=conflict_analysis
        )
    
    def build_failure(
        self,
        error_message: str,
        error_code: str,
        suggestions: Optional[List[str]] = None
    ) -> FDCResponse:
        """Costruisce risposta di fallimento."""
        conflict_analysis = ConflictAnalysis(
            original_conflicts=self.original_conflicts,
            resolved_conflicts=0,
            remaining_conflicts=len(self.original_conflicts),
            unresolved_details=self.unresolved_conflicts if self.unresolved_conflicts else None
        )
        
        return FDCResponse(
            success=False,
            modifications=[],
            total_impact_minutes=0.0,
            ml_confidence=0.0,
            error_message=error_message,
            error_code=error_code,
            suggestions=suggestions,
            conflict_analysis=conflict_analysis
        )


def create_minimal_fdc_response(
    train_id: str,
    origin_station: str,
    delay_seconds: int,
    affected_stations: List[str],
    reason: str,
    confidence: float = 0.85
) -> Dict[str, Any]:
    """
    Crea risposta FDC minimale (backward compatible).
    
    Da usare quando non si hanno informazioni dettagliate.
    """
    builder = FDCIntegrationBuilder()
    builder.add_departure_delay(
        train_id=train_id,
        station=origin_station,
        delay_seconds=delay_seconds,
        affected_stations=affected_stations,
        reason=reason,
        confidence=confidence
    )
    builder.set_ml_confidence(confidence)
    
    response = builder.build_success()
    return response.to_dict()
