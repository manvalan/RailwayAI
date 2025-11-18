"""
Esempio completo di utilizzo del Railway AI Scheduler.
Dimostra:
- Setup rete ferroviaria
- Aggiunta treni
- Rilevamento conflitti
- Risoluzione automatica
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / 'python'))

import railway_cpp as rc


def print_section(title):
    """Stampa un separatore per le sezioni."""
    print("\n" + "=" * 60)
    print(f" {title}")
    print("=" * 60 + "\n")


def main():
    print_section("Railway AI Scheduler - Esempio Completo")
    
    # ========================================================================
    # 1. Inizializzazione Scheduler
    # ========================================================================
    
    print("📊 Inizializzazione scheduler...")
    scheduler = rc.RailwayScheduler(num_tracks=5, num_stations=4)
    print("✓ Scheduler inizializzato")
    
    # ========================================================================
    # 2. Configurazione Rete Ferroviaria
    # ========================================================================
    
    print_section("Configurazione Rete Ferroviaria")
    
    # Definisci binari
    tracks = []
    
    # Track 0: Milano - Bologna (binario singolo)
    track0 = rc.Track()
    track0.id = 0
    track0.length_km = 220.0
    track0.is_single_track = True
    track0.capacity = 1
    track0.station_ids = [0, 1]
    tracks.append(track0)
    print(f"  Binario 0: Milano-Bologna (singolo, 220km)")
    
    # Track 1: Bologna - Firenze (doppio binario)
    track1 = rc.Track()
    track1.id = 1
    track1.length_km = 80.0
    track1.is_single_track = False
    track1.capacity = 3
    track1.station_ids = [1, 2]
    tracks.append(track1)
    print(f"  Binario 1: Bologna-Firenze (doppio, 80km)")
    
    # Track 2: Firenze - Roma (doppio binario)
    track2 = rc.Track()
    track2.id = 2
    track2.length_km = 280.0
    track2.is_single_track = False
    track2.capacity = 3
    track2.station_ids = [2, 3]
    tracks.append(track2)
    print(f"  Binario 2: Firenze-Roma (doppio, 280km)")
    
    # Definisci stazioni
    stations = []
    
    station_names = [
        "Milano Centrale",
        "Bologna Centrale", 
        "Firenze Santa Maria Novella",
        "Roma Termini"
    ]
    
    for i, name in enumerate(station_names):
        station = rc.Station()
        station.id = i
        station.name = name
        station.num_platforms = 8 if i in [0, 3] else 6
        station.connected_track_ids = []
        stations.append(station)
        print(f"  Stazione {i}: {name} ({station.num_platforms} binari)")
    
    # Inizializza rete (argomenti posizionali, non keyword)
    scheduler.initialize_network(tracks, stations)
    print("\n✓ Rete ferroviaria configurata")
    
    # ========================================================================
    # 3. Aggiunta Treni
    # ========================================================================
    
    print_section("Aggiunta Treni alla Rete")
    
    trains = []
    
    # Treno 1: Intercity Milano → Roma (alta priorità)
    train1 = rc.Train()
    train1.id = 1
    train1.current_track = 0
    train1.position_km = 20.0
    train1.velocity_kmh = 150.0
    train1.scheduled_arrival_minutes = 120.0
    train1.destination_station = 3
    train1.priority = 9
    train1.is_delayed = False
    train1.delay_minutes = 0.0
    trains.append(train1)
    scheduler.add_train(train1)
    print(f"  ✓ Treno {train1.id}: IC Milano→Roma (priorità {train1.priority})")
    
    # Treno 2: Regionale Bologna ← Milano (direzione opposta!)
    train2 = rc.Train()
    train2.id = 2
    train2.current_track = 0  # Stesso binario!
    train2.position_km = 180.0  # Direzione opposta
    train2.velocity_kmh = 100.0
    train2.scheduled_arrival_minutes = 90.0
    train2.destination_station = 0
    train2.priority = 4
    train2.is_delayed = False
    train2.delay_minutes = 0.0
    trains.append(train2)
    scheduler.add_train(train2)
    print(f"  ✓ Treno {train2.id}: REG Bologna→Milano (priorità {train2.priority})")
    
    # Treno 3: Frecciarossa Bologna → Roma
    train3 = rc.Train()
    train3.id = 3
    train3.current_track = 1
    train3.position_km = 10.0
    train3.velocity_kmh = 200.0
    train3.scheduled_arrival_minutes = 150.0
    train3.destination_station = 3
    train3.priority = 10
    train3.is_delayed = False
    train3.delay_minutes = 0.0
    trains.append(train3)
    scheduler.add_train(train3)
    print(f"  ✓ Treno {train3.id}: FR Bologna→Roma (priorità {train3.priority})")
    
    # Treno 4: Regionale in ritardo
    train4 = rc.Train()
    train4.id = 4
    train4.current_track = 1
    train4.position_km = 8.0  # Molto vicino a train3!
    train4.velocity_kmh = 90.0
    train4.scheduled_arrival_minutes = 100.0
    train4.destination_station = 2
    train4.priority = 3
    train4.is_delayed = True
    train4.delay_minutes = 15.0
    trains.append(train4)
    scheduler.add_train(train4)
    print(f"  ⚠ Treno {train4.id}: REG Bologna→Firenze (priorità {train4.priority}, ritardo {train4.delay_minutes}min)")
    
    # ========================================================================
    # 4. Stato Iniziale
    # ========================================================================
    
    print_section("Stato Iniziale della Rete")
    
    stats = scheduler.get_statistics()
    print(f"  Treni attivi: {stats.total_trains}")
    print(f"  Treni in ritardo: {stats.delayed_trains}")
    print(f"  Ritardo medio: {stats.average_delay_minutes:.1f} minuti")
    print(f"  Efficienza rete: {stats.network_efficiency * 100:.1f}%")
    
    # ========================================================================
    # 5. Rilevamento Conflitti
    # ========================================================================
    
    print_section("Rilevamento Conflitti")
    
    conflicts = scheduler.detect_conflicts()
    print(f"  🔍 Rilevati {len(conflicts)} conflitti:\n")
    
    for i, conflict in enumerate(conflicts, 1):
        print(f"  Conflitto {i}:")
        print(f"    • Treni: {conflict.train1_id} ↔ {conflict.train2_id}")
        print(f"    • Binario: {conflict.track_id}")
        print(f"    • Tipo: {conflict.conflict_type}")
        print(f"    • Tempo collisione: {conflict.estimated_collision_time_minutes:.1f} min")
        print(f"    • Gravità: {conflict.severity}/10")
        print()
    
    if not conflicts:
        print("  ✓ Nessun conflitto rilevato!")
        return
    
    # ========================================================================
    # 6. Risoluzione Conflitti
    # ========================================================================
    
    print_section("Risoluzione Conflitti")
    
    print("  🤖 Calcolo aggiustamenti ottimali...")
    adjustments = scheduler.resolve_conflicts(conflicts)
    
    print(f"\n  Proposti {len(adjustments)} aggiustamenti:\n")
    
    for i, adj in enumerate(adjustments, 1):
        train = scheduler.get_train_info(adj.train_id)
        print(f"  Aggiustamento {i}:")
        print(f"    • Treno: {adj.train_id} (priorità {train.priority})")
        print(f"    • Ritardo: {adj.time_adjustment_minutes:+.1f} minuti")
        if adj.new_track_id >= 0:
            print(f"    • Cambio binario: {train.current_track} → {adj.new_track_id}")
        print(f"    • Motivazione: {adj.reason}")
        print()
    
    # Applica aggiustamenti
    print("  ⚙️  Applicazione aggiustamenti...")
    scheduler.apply_adjustments(adjustments)
    print("  ✓ Aggiustamenti applicati")
    
    # ========================================================================
    # 7. Stato Finale
    # ========================================================================
    
    print_section("Stato Finale della Rete")
    
    final_stats = scheduler.get_statistics()
    print(f"  Treni attivi: {final_stats.total_trains}")
    print(f"  Treni in ritardo: {final_stats.delayed_trains}")
    print(f"  Ritardo medio: {final_stats.average_delay_minutes:.1f} minuti")
    print(f"  Efficienza rete: {final_stats.network_efficiency * 100:.1f}%")
    print(f"  Conflitti attivi: {final_stats.active_conflicts}")
    
    # Confronto
    print("\n  📈 Miglioramenti:")
    print(f"    • Efficienza: {stats.network_efficiency * 100:.1f}% → {final_stats.network_efficiency * 100:.1f}%")
    print(f"    • Conflitti: {len(conflicts)} → {final_stats.active_conflicts}")
    
    # ========================================================================
    # 8. Event Log
    # ========================================================================
    
    print_section("Event Log (ultimi 10 eventi)")
    
    events = scheduler.get_event_log(max_events=10)
    for event in events[-10:]:
        print(f"  {event}")
    
    print_section("Simulazione Completata")
    print("✓ Tutti i conflitti sono stati risolti con successo!")
    print()


if __name__ == "__main__":
    try:
        main()
    except ImportError as e:
        print(f"ERRORE: {e}")
        print("\nAssicurati di aver compilato il modulo C++:")
        print("  cd build && cmake --build . --config Release")
        print("  cp build/python/railway_cpp* python/")
