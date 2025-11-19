#!/usr/bin/env python3
"""
Demo: Gestione conflitti in stazione multi-binario collegata a linee a binario unico.

Scenario:
    Linea A (binario unico) ←--[Treno 1]-- STAZIONE (2 binari) --[Treno 2]--→ Linea B (binario unico)
    
    Due treni arrivano da direzioni opposte su linee a binario unico e devono 
    convergere nella stazione. Il sistema deve:
    1. Assegnare binari diversi ai treni in arrivo
    2. Gestire precedenze se i binari sono occupati
    3. Evitare deadlock
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'build', 'python'))

import railway_cpp as rc

def print_section(title):
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}\n")

def create_single_track_scenario():
    """
    Crea uno scenario con:
    - Track 0: Linea principale (binario unico, 50km)
    - Track 1,2,3: Altri binari per test
    
    Simula conflitti su binario singolo con possibilità di deviazione
    """
    
    scheduler = rc.RailwayScheduler(num_tracks=4, num_stations=2)
    
    # Crea binari
    tracks = []
    
    # Track 0: Linea principale (binario unico)
    track0 = rc.Track()
    track0.id = 0
    track0.length_km = 50.0
    track0.is_single_track = True
    track0.capacity = 1
    track0.station_ids = [0, 1]
    tracks.append(track0)
    
    # Track 1: Binario alternativo (multi-track in stazione)
    track1 = rc.Track()
    track1.id = 1
    track1.length_km = 50.0
    track1.is_single_track = False
    track1.capacity = 3
    track1.station_ids = [0, 1]
    tracks.append(track1)
    
    # Track 2: Altro binario
    track2 = rc.Track()
    track2.id = 2
    track2.length_km = 50.0
    track2.is_single_track = False
    track2.capacity = 2
    track2.station_ids = [0, 1]
    tracks.append(track2)
    
    # Track 3: Altro binario
    track3 = rc.Track()
    track3.id = 3
    track3.length_km = 50.0
    track3.is_single_track = False
    track3.capacity = 2
    track3.station_ids = [0, 1]
    tracks.append(track3)
    
    # Crea stazioni
    stations = []
    
    station0 = rc.Station()
    station0.id = 0
    station0.name = "Stazione Ovest"
    station0.num_platforms = 4
    station0.connected_track_ids = [0, 1, 2, 3]
    stations.append(station0)
    
    station1 = rc.Station()
    station1.id = 1
    station1.name = "Stazione Est"
    station1.num_platforms = 4
    station1.connected_track_ids = [0, 1, 2, 3]
    stations.append(station1)
    
    scheduler.initialize_network(tracks, stations)
    
    return scheduler

def scenario_1_opposite_directions():
    """
    Scenario 1: Due treni da direzioni opposte
    - Treno 101: Arriva da Ovest (Track 1) verso stazione
    - Treno 102: Arriva da Est (Track 3) verso stazione
    """
    print_section("SCENARIO 1: Treni da Direzioni Opposte")
    
    scheduler = create_single_track_scenario()
    
    # Treno 101: Da Ovest, su binario 0
    train1 = rc.Train()
    train1.id = 101
    train1.current_track = 0  # Prima linea
    train1.position_km = 15.0  # Sulla linea
    train1.velocity_kmh = 100.0
    train1.destination_station = 1
    train1.priority = 7
    train1.is_delayed = False
    train1.delay_minutes = 0.0
    
    # Treno 102: Da Est, su binario 1 (stessa direzione per creare conflitto)
    train2 = rc.Train()
    train2.id = 102
    train2.current_track = 0  # Stessa linea del train1 -> conflitto
    train2.position_km = 25.0  # Più avanti
    train2.velocity_kmh = 80.0  # Più lento -> train1 lo raggiungerà
    train2.destination_station = 1
    train2.priority = 6
    train2.is_delayed = False
    train2.delay_minutes = 0.0
    
    scheduler.add_train(train1)
    scheduler.add_train(train2)
    
    print("Configurazione iniziale:")
    print(f"  Treno 101: Track 0, pos=15km, vel=100km/h, dest=Stazione 1, priorità=7")
    print(f"  Treno 102: Track 0, pos=25km, vel=80km/h, dest=Stazione 1, priorità=6")
    print(f"\n  → Entrambi su stesso binario, train1 più veloce raggiungerà train2")
    
    # Rileva conflitti
    conflicts = scheduler.detect_conflicts()
    print(f"\n✗ Conflitti rilevati: {len(conflicts)}")
    
    for i, conflict in enumerate(conflicts, 1):
        print(f"\n  Conflitto {i}:")
        print(f"    Treni: {conflict.train1_id} vs {conflict.train2_id}")
        print(f"    Track: {conflict.track_id}")
        print(f"    Tipo: {conflict.conflict_type}")
        print(f"    Gravità: {conflict.severity}/10")
        print(f"    Tempo stimato collisione: {conflict.estimated_collision_time_minutes:.1f} min")
    
    # Risolvi con strategia binario singolo
    print("\n📋 Risoluzione con strategia binario singolo...")
    adjustments = scheduler.resolve_conflicts(conflicts)
    
    print(f"\n✓ Soluzioni trovate: {len(adjustments)}")
    
    for i, adj in enumerate(adjustments, 1):
        print(f"\n  Soluzione {i}:")
        print(f"    Treno: {adj.train_id}")
        print(f"    Ritardo: {adj.time_adjustment_minutes:.1f} min")
        print(f"    Nuovo binario: {adj.new_track_id if adj.new_track_id != -1 else 'Nessun cambio'}")
        print(f"    Confidenza: {adj.confidence*100:.0f}%")
        print(f"    Motivo: {adj.reason}")
    
    return scheduler

def scenario_2_priority_conflict():
    """
    Scenario 2: Tre treni, uno ad alta priorità
    - Treno 201: Alta priorità
    - Treno 202: Bassa priorità
    - Treno 203: Media priorità
    """
    print_section("SCENARIO 2: Conflitto con Priorità Diverse")
    
    scheduler = create_single_track_scenario()
    
    # Treno 201: Alta priorità
    train1 = rc.Train()
    train1.id = 201
    train1.current_track = 0
    train1.position_km = 10.0
    train1.velocity_kmh = 120.0
    train1.destination_station = 1
    train1.priority = 9  # ALTA priorità
    train1.is_delayed = False
    train1.delay_minutes = 0.0
    
    # Treno 202: Bassa priorità
    train2 = rc.Train()
    train2.id = 202
    train2.current_track = 0
    train2.position_km = 20.0
    train2.velocity_kmh = 90.0
    train2.destination_station = 1
    train2.priority = 4  # BASSA priorità
    train2.is_delayed = False
    train2.delay_minutes = 0.0
    
    # Treno 203: Media priorità
    train3 = rc.Train()
    train3.id = 203
    train3.current_track = 0
    train3.position_km = 15.0
    train3.velocity_kmh = 100.0
    train3.destination_station = 1
    train3.priority = 6  # MEDIA priorità
    train3.is_delayed = False
    train3.delay_minutes = 0.0
    
    scheduler.add_train(train1)
    scheduler.add_train(train2)
    scheduler.add_train(train3)
    
    print("Configurazione iniziale:")
    print(f"  Treno 201: Track 0, pos=10km, priorità=9 (ALTA)")
    print(f"  Treno 202: Track 0, pos=20km, priorità=4 (BASSA)")
    print(f"  Treno 203: Track 0, pos=15km, priorità=6 (MEDIA)")
    
    conflicts = scheduler.detect_conflicts()
    print(f"\n✗ Conflitti rilevati: {len(conflicts)}")
    
    adjustments = scheduler.resolve_conflicts(conflicts)
    print(f"\n✓ Soluzioni trovate: {len(adjustments)}")
    
    for i, adj in enumerate(adjustments, 1):
        print(f"\n  Soluzione {i}:")
        print(f"    Treno: {adj.train_id}")
        print(f"    Ritardo: {adj.time_adjustment_minutes:.1f} min")
        print(f"    Nuovo binario: {adj.new_track_id if adj.new_track_id != -1 else 'Nessun cambio'}")
        print(f"    Confidenza: {adj.confidence*100:.0f}%")
        print(f"    Motivo: {adj.reason}")
    
    print("\n📊 Analisi:")
    print(f"  → Il treno 201 (priorità 9) dovrebbe passare per primo")
    print(f"  → I treni 202 e 203 dovrebbero essere deviati o ritardati")
    
    return scheduler

def scenario_3_station_full():
    """
    Scenario 3: Binario saturo
    - Più treni sulla stessa linea
    - Sistema deve gestire capacità limitata
    """
    print_section("SCENARIO 3: Binario Saturo")
    
    scheduler = create_single_track_scenario()
    
    # Treno 301: In testa
    train1 = rc.Train()
    train1.id = 301
    train1.current_track = 0
    train1.position_km = 30.0
    train1.velocity_kmh = 80.0
    train1.destination_station = 1
    train1.priority = 5
    train1.is_delayed = False
    train1.delay_minutes = 0.0
    
    # Treno 302: Nel mezzo
    train2 = rc.Train()
    train2.id = 302
    train2.current_track = 0
    train2.position_km = 20.0
    train2.velocity_kmh = 100.0
    train2.destination_station = 1
    train2.priority = 7
    train2.is_delayed = False
    train2.delay_minutes = 0.0
    
    # Treno 303: In coda
    train3 = rc.Train()
    train3.id = 303
    train3.current_track = 0
    train3.position_km = 10.0
    train3.velocity_kmh = 110.0
    train3.destination_station = 1
    train3.priority = 6
    train3.is_delayed = False
    train3.delay_minutes = 0.0
    
    scheduler.add_train(train1)
    scheduler.add_train(train2)
    scheduler.add_train(train3)
    
    print("Configurazione iniziale:")
    print(f"  Treno 301: Track 0, pos=30km, vel=80km/h (lento)")
    print(f"  Treno 302: Track 0, pos=20km, vel=100km/h (medio)")
    print(f"  Treno 303: Track 0, pos=10km, vel=110km/h (veloce)")
    print(f"\n  → Tutti su stesso binario, i veloci raggiungeranno i lenti")
    
    conflicts = scheduler.detect_conflicts()
    print(f"\n✗ Conflitti rilevati: {len(conflicts)}")
    
    adjustments = scheduler.resolve_conflicts(conflicts)
    print(f"\n✓ Soluzioni trovate: {len(adjustments)}")
    
    for i, adj in enumerate(adjustments, 1):
        print(f"\n  Soluzione {i}:")
        print(f"    Treno: {adj.train_id}")
        print(f"    Ritardo: {adj.time_adjustment_minutes:.1f} min")
        print(f"    Nuovo binario: {adj.new_track_id if adj.new_track_id != -1 else 'Nessun cambio'}")
        print(f"    Confidenza: {adj.confidence*100:.0f}%")
        print(f"    Motivo: {adj.reason}")
    
    print("\n📊 Analisi:")
    print(f"  → Tre treni su stesso binario con velocità diverse")
    print(f"  → Sistema deve gestire sorpassi o ritardi")
    print(f"  → Possibile deviazione su binari alternativi se disponibili")
    
    return scheduler

if __name__ == "__main__":
    print("""
╔═══════════════════════════════════════════════════════════════════════════╗
║                                                                           ║
║   DEMO: Gestione Conflitti Stazione Multi-Binario + Binari Unici         ║
║                                                                           ║
║   Problema: Due linee a binario unico (direzioni opposte) convergono     ║
║   in una stazione con più binari. Come gestire i conflitti?              ║
║                                                                           ║
╚═══════════════════════════════════════════════════════════════════════════╝
    """)
    
    # Esegui scenari
    scenario_1_opposite_directions()
    scenario_2_priority_conflict()
    scenario_3_station_full()
    
    print_section("RIEPILOGO STRATEGIA")
    print("""
La strategia implementata:

1. DEVIAZIONE IN STAZIONE (Preferita)
   → Se treno entro 10km da stazione
   → Cerca binari multi-track disponibili
   → Devia su binario con meno congestione
   → Ritardo: 1.0 min (solo manovra)
   → Confidenza: 85%

2. ATTESA PER PRIORITÀ (Fallback)
   → Se deviazione non possibile
   → Treno con priorità minore aspetta
   → Ritardo: 8 min × numero treni in conflitto
   → Confidenza: 70%

Vantaggi:
✓ Previene deadlock su binari unici
✓ Utilizza capacità stazione in modo efficiente
✓ Rispetta priorità dei treni
✓ Ritardi minimi (1 min vs 8+ min)
    """)
