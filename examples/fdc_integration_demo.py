"""
Test ed esempio di utilizzo del modulo FDC Integration.

Dimostra come costruire risposte conformi alle specifiche FDC.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from python.integration.fdc_integration import (
    FDCIntegrationBuilder,
    ConflictType,
    create_minimal_fdc_response
)
import json


def example_1_platform_change():
    """
    Esempio 1: Risoluzione conflitto con cambio binario (ZERO DELAY).
    
    Scenario: IC101 e R203 arrivano entrambi a MONZA sul binario 1.
    Soluzione: Sposta R203 al binario 2 → conflitto risolto senza ritardi!
    """
    print("\n" + "="*80)
    print("📍 ESEMPIO 1: CAMBIO BINARIO (Zero Delay)")
    print("="*80)
    
    builder = FDCIntegrationBuilder()
    
    # Aggiungi conflitto originale
    builder.add_conflict(
        conflict_type=ConflictType.PLATFORM_CONFLICT,
        location="MONZA",
        trains=["IC101", "R203"],
        severity="high",
        time_overlap_seconds=300
    )
    
    # Soluzione primaria: cambio binario
    builder.add_platform_change(
        train_id="R203",
        station="MONZA",
        new_platform=2,
        original_platform=1,
        affected_stations=["MONZA"],
        reason="Cambio binario risolve conflitto senza ritardi",
        confidence=0.96
    )
    
    builder.set_ml_confidence(0.96)
    builder.set_optimization_type("platform_reassignment")
    
    # Alternativa: ritardo
    alt_builder = FDCIntegrationBuilder()
    alt_builder.add_departure_delay(
        train_id="IC101",
        station="MILANO_CENTRALE",
        delay_seconds=180,
        affected_stations=["MILANO_CENTRALE", "MONZA", "COMO"],
        reason="Ritardo partenza alternativo",
        confidence=0.88
    )
    
    builder.add_alternative(
        description="Ritardo IC101 di 3 minuti",
        modifications=alt_builder.modifications,
        confidence=0.88
    )
    
    response = builder.build_success()
    
    print("\n✅ Risposta generata:")
    print(json.dumps(response.to_dict(), indent=2, ensure_ascii=False))
    
    print(f"\n📊 Metriche:")
    print(f"   Ritardo totale: {response.total_impact_minutes} minuti")
    print(f"   Conflitti risolti: {response.conflict_analysis.resolved_conflicts}")
    print(f"   Alternative fornite: {len(response.alternatives) if response.alternatives else 0}")
    print(f"   ML Confidence: {response.ml_confidence:.1%}")


def example_2_speed_reduction():
    """
    Esempio 2: Riduzione velocità su tratta specifica.
    
    Scenario: IC101 troppo veloce, raggiungerebbe MONZA in conflitto con R203.
    Soluzione: Riduce velocità da 140 a 100 km/h sulla tratta MILANO-MONZA.
    """
    print("\n" + "="*80)
    print("🐌 ESEMPIO 2: RIDUZIONE VELOCITÀ")
    print("="*80)
    
    builder = FDCIntegrationBuilder()
    
    builder.add_conflict(
        conflict_type=ConflictType.TIMING_CONFLICT,
        location="MONZA",
        trains=["IC101", "R203"],
        severity="medium",
        time_overlap_seconds=120
    )
    
    # Riduzione velocità
    builder.add_speed_modification(
        train_id="IC101",
        from_station="MILANO_CENTRALE",
        to_station="MONZA",
        new_speed_kmh=100.0,
        original_speed_kmh=140.0,
        time_increase_seconds=180,
        affected_stations=["MONZA", "COMO"],
        reason="Riduzione velocità per coordinamento con R203",
        confidence=0.95
    )
    
    builder.set_ml_confidence(0.95)
    builder.set_optimization_type("speed_coordination")
    
    response = builder.build_success()
    
    print("\n✅ Risposta generata:")
    print(json.dumps(response.to_dict(), indent=2, ensure_ascii=False))


def example_3_multi_train_coordination():
    """
    Esempio 3: Coordinamento multi-treno complesso.
    
    Scenario: 3 treni con conflitti multipli.
    Soluzione: Combinazione di cambio binario, riduzione velocità e aumento sosta.
    """
    print("\n" + "="*80)
    print("🚦 ESEMPIO 3: COORDINAMENTO MULTI-TRENO")
    print("="*80)
    
    builder = FDCIntegrationBuilder()
    
    # Conflitti multipli
    builder.add_conflict(
        conflict_type=ConflictType.PLATFORM_CONFLICT,
        location="MONZA",
        trains=["IC101", "R203"],
        severity="high"
    )
    
    builder.add_conflict(
        conflict_type=ConflictType.SPEED_CONFLICT,
        location="COMO",
        trains=["R203", "R205"],
        severity="medium"
    )
    
    # Modifica 1: Riduzione velocità IC101
    builder.add_speed_modification(
        train_id="IC101",
        from_station="MILANO_CENTRALE",
        to_station="MONZA",
        new_speed_kmh=100.0,
        original_speed_kmh=140.0,
        time_increase_seconds=180,
        affected_stations=["MONZA", "COMO"],
        reason="Riduzione velocità per coordinamento con R203",
        confidence=0.95
    )
    
    # Modifica 2: Cambio binario R203
    builder.add_platform_change(
        train_id="R203",
        station="MONZA",
        new_platform=2,
        original_platform=1,
        affected_stations=["MONZA"],
        reason="Cambio binario per evitare conflitto con IC101",
        confidence=0.98
    )
    
    # Modifica 3: Aumento sosta R205
    builder.add_dwell_time_change(
        train_id="R205",
        station="COMO",
        additional_seconds=120,
        original_dwell_seconds=180,
        affected_stations=["MONZA", "MILANO_CENTRALE"],
        reason="Aumento sosta per separazione temporale",
        confidence=0.88
    )
    
    builder.set_ml_confidence(0.92)
    builder.set_optimization_type("multi_train_coordination")
    
    response = builder.build_success()
    
    print("\n✅ Risposta generata:")
    print(json.dumps(response.to_dict(), indent=2, ensure_ascii=False))
    
    print(f"\n📊 Riepilogo:")
    print(f"   Treni modificati: {len(set(m.train_id for m in response.modifications))}")
    print(f"   Modifiche totali: {len(response.modifications)}")
    print(f"   Ritardo totale: {response.total_impact_minutes:.1f} minuti")
    print(f"   Conflitti originali: {len(response.conflict_analysis.original_conflicts)}")
    print(f"   Conflitti risolti: {response.conflict_analysis.resolved_conflicts}")


def example_4_failure_response():
    """
    Esempio 4: Risposta di fallimento quando l'ottimizzazione non è possibile.
    """
    print("\n" + "="*80)
    print("❌ ESEMPIO 4: FALLIMENTO OTTIMIZZAZIONE")
    print("="*80)
    
    builder = FDCIntegrationBuilder()
    
    # Conflitti irrisolvibili
    builder.add_conflict(
        conflict_type=ConflictType.CAPACITY_CONFLICT,
        location="MONZA",
        trains=["IC101", "R203", "IC104", "R207"],
        severity="high"
    )
    
    response = builder.build_failure(
        error_message="Impossibile risolvere conflitti senza violare vincoli di capacità",
        error_code="CAPACITY_EXCEEDED",
        suggestions=[
            "Ridurre il numero di treni nella finestra oraria 08:00-09:00",
            "Aumentare capacità binari alla stazione MONZA",
            "Considerare percorsi alternativi via SARONNO"
        ]
    )
    
    print("\n❌ Risposta di fallimento:")
    print(json.dumps(response.to_dict(), indent=2, ensure_ascii=False))


def example_5_minimal_backward_compatible():
    """
    Esempio 5: Formato minimale backward-compatible.
    
    Per sistemi legacy che non supportano ancora tutte le feature.
    """
    print("\n" + "="*80)
    print("🔄 ESEMPIO 5: FORMATO MINIMALE (Backward Compatible)")
    print("="*80)
    
    response = create_minimal_fdc_response(
        train_id="IC101",
        origin_station="MILANO_CENTRALE",
        delay_seconds=180,
        affected_stations=["MILANO_CENTRALE", "MONZA", "COMO"],
        reason="Ritardo partenza per evitare conflitto",
        confidence=0.85
    )
    
    print("\n✅ Risposta minimale:")
    print(json.dumps(response, indent=2, ensure_ascii=False))


def run_all_examples():
    """Esegue tutti gli esempi."""
    print("\n" + "="*80)
    print("🚂 TEST FDC INTEGRATION MODULE")
    print("   Esempi conformi a RAILWAY_AI_INTEGRATION_SPECS.md")
    print("="*80)
    
    example_1_platform_change()
    example_2_speed_reduction()
    example_3_multi_train_coordination()
    example_4_failure_response()
    example_5_minimal_backward_compatible()
    
    print("\n" + "="*80)
    print("✅ TUTTI GLI ESEMPI COMPLETATI")
    print("="*80)
    
    print("\n📝 Esempi dimostrati:")
    print("   1. Cambio binario (zero delay)")
    print("   2. Riduzione velocità su tratta")
    print("   3. Coordinamento multi-treno complesso")
    print("   4. Gestione fallimento ottimizzazione")
    print("   5. Formato minimale backward-compatible")
    
    print("\n💡 Prossimi passi:")
    print("   • Integrare con railway_scheduler.cpp esistente")
    print("   • Creare endpoint API che usa questo formato")
    print("   • Testare con dati reali FDC")
    print("   • Implementare ML model per scegliere modification_type ottimale")


if __name__ == '__main__':
    run_all_examples()
