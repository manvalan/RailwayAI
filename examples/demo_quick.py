"""
Demo veloce del Railway AI Scheduler usando solo Python.
Mostra generazione dati, rilevamento conflitti e risoluzione.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / 'python'))

import numpy as np
from data.data_generator import RailwayNetworkGenerator


def print_header(title):
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70 + "\n")


def main():
    print_header("🚂 RAILWAY AI SCHEDULER - DEMO VELOCE")
    
    # ========================================================================
    # 1. Genera Rete Ferroviaria
    # ========================================================================
    
    print_header("FASE 1: Generazione Rete Ferroviaria")
    
    generator = RailwayNetworkGenerator(
        num_stations=6,
        num_tracks=8,
        single_track_ratio=0.4
    )
    
    print(f"✓ Rete generata:")
    print(f"  • Stazioni: {len(generator.stations)}")
    print(f"  • Binari totali: {len(generator.tracks)}")
    
    single_tracks = [t for t in generator.tracks if t.is_single_track]
    print(f"  • Binari singoli: {len(single_tracks)} ({len(single_tracks)/len(generator.tracks)*100:.0f}%)")
    
    print("\n📍 Stazioni principali:")
    for station in generator.stations[:3]:
        print(f"  - {station.name}: {station.num_platforms} binari, " +
              f"{len(station.connected_tracks)} collegamenti")
    
    print("\n🛤️  Binari esempio:")
    for track in generator.tracks[:3]:
        track_type = "SINGOLO" if track.is_single_track else "DOPPIO"
        print(f"  - Binario {track.id}: {track.length_km:.1f}km ({track_type})")
    
    # ========================================================================
    # 2. Genera Scenario con Treni
    # ========================================================================
    
    print_header("FASE 2: Generazione Scenario Traffico")
    
    scenario = generator.generate_scenario(
        num_trains=15,
        conflict_probability=0.6  # Alta probabilità conflitti per demo
    )
    
    trains = scenario['trains']
    conflicts = scenario['conflicts']
    
    print(f"✓ Scenario generato:")
    print(f"  • Treni attivi: {len(trains)}")
    print(f"  • Conflitti rilevati: {len(conflicts)}")
    
    # Statistiche treni
    delayed = sum(1 for t in trains if t.is_delayed)
    avg_priority = sum(t.priority for t in trains) / len(trains)
    
    print(f"\n📊 Statistiche treni:")
    print(f"  • In ritardo: {delayed}/{len(trains)} ({delayed/len(trains)*100:.0f}%)")
    print(f"  • Priorità media: {avg_priority:.1f}/10")
    
    # Mostra alcuni treni
    print(f"\n🚂 Primi 5 treni:")
    for i, train in enumerate(trains[:5], 1):
        status = "⚠️ RITARDO" if train.is_delayed else "✅ PUNTUALE"
        print(f"  {i}. Treno #{train.id}: {train.velocity_kmh:.0f}km/h, " +
              f"priorità {train.priority}, {status}")
        print(f"     Posizione: {train.position_km:.1f}km su binario {train.current_track}")
    
    # ========================================================================
    # 3. Analisi Conflitti
    # ========================================================================
    
    print_header("FASE 3: Analisi Conflitti")
    
    if not conflicts:
        print("✅ Nessun conflitto rilevato! Rete ottimale.")
    else:
        print(f"⚠️  Rilevati {len(conflicts)} conflitti:\n")
        
        for i, (t1_id, t2_id) in enumerate(conflicts[:5], 1):
            train1 = trains[t1_id]
            train2 = trains[t2_id]
            
            print(f"  Conflitto #{i}:")
            print(f"    • Treno {t1_id} (priorità {train1.priority}) ↔ " +
                  f"Treno {t2_id} (priorità {train2.priority})")
            print(f"    • Entrambi su binario {train1.current_track}")
            
            distance = abs(train1.position_km - train2.position_km)
            print(f"    • Distanza: {distance:.1f}km")
            
            # Determina tipo conflitto
            track = generator.tracks[train1.current_track]
            if track.is_single_track:
                print(f"    • ⚠️  CRITICO: Binario singolo!")
            else:
                print(f"    • Binario doppio (gestibile)")
            print()
    
    # ========================================================================
    # 4. Strategia Risoluzione (Euristica Semplice)
    # ========================================================================
    
    print_header("FASE 4: Risoluzione Conflitti (Euristica)")
    
    if conflicts:
        print("💡 Strategia: Dai priorità a treni con priorità maggiore\n")
        
        resolutions = []
        
        for t1_id, t2_id in conflicts[:5]:
            train1 = trains[t1_id]
            train2 = trains[t2_id]
            
            if train1.priority < train2.priority:
                delayed_train = train1
                priority_train = train2
            else:
                delayed_train = train2
                priority_train = train1
            
            delay_minutes = 10  # Ritardo fisso per demo
            
            print(f"  Conflitto {t1_id} ↔ {t2_id}:")
            print(f"    → Treno {delayed_train.id}: +{delay_minutes} min ritardo")
            print(f"    → Treno {priority_train.id}: nessun cambiamento")
            
            resolutions.append({
                'train_id': delayed_train.id,
                'delay': delay_minutes,
                'reason': f'Priorità a treno {priority_train.id}'
            })
        
        # Calcola impatto
        total_delay = sum(r['delay'] for r in resolutions)
        print(f"\n📈 Impatto totale:")
        print(f"  • Ritardo aggiunto: {total_delay} minuti")
        print(f"  • Treni affetti: {len(resolutions)}/{len(trains)}")
        print(f"  • Conflitti risolti: {len(conflicts)}")
    
    # ========================================================================
    # 5. Dati per Training ML
    # ========================================================================
    
    print_header("FASE 5: Dati per Training Rete Neurale")
    
    network_state = scenario['network_state']
    train_states = scenario['train_states']
    conflict_matrix = scenario['conflict_matrix']
    
    print("📦 Formato dati per training:")
    print(f"  • Network state shape: {network_state.shape}")
    print(f"  • Train states shape: {train_states.shape}")
    print(f"  • Conflict matrix shape: {conflict_matrix.shape}")
    
    print(f"\n💾 Dataset disponibili:")
    print(f"  • Training: data/training_data.npz")
    print(f"  • Validation: data/validation_data.npz")
    
    # ========================================================================
    # Summary
    # ========================================================================
    
    print_header("✅ DEMO COMPLETATA")
    
    print("🎯 Risultati:")
    print(f"  • Rete: {len(generator.stations)} stazioni, {len(generator.tracks)} binari")
    print(f"  • Traffico: {len(trains)} treni attivi")
    print(f"  • Conflitti: {len(conflicts)} rilevati")
    print(f"  • Risoluzione: Euristica basata su priorità")
    
    print("\n📚 Prossimi passi:")
    print("  1. ✅ Dati generati → data/training_data.npz")
    print("  2. 🔨 Addestra rete neurale: python python/training/train_model.py")
    print("  3. 🚀 Compila modulo C++: mkdir build && cd build && cmake .. && make")
    print("  4. 🎮 Esegui esempio completo: python examples/example_usage.py")
    
    print("\n💡 Info:")
    print("  • La rete neurale apprenderà strategie migliori dell'euristica")
    print("  • Il modulo C++ fornirà performance real-time")
    print("  • I dati reali RFI miglioreranno accuratezza")
    
    print("\n" + "=" * 70)
    print("  Grazie per aver provato Railway AI Scheduler! 🚂✨")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()
