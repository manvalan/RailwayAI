"""
Playground per sperimentare con diversi scenari ferroviari.
Modifica i parametri per vedere come cambiano conflitti e complessità.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / 'python'))

from data.data_generator import RailwayNetworkGenerator
import numpy as np


def experiment_single_vs_double_track():
    """Confronta scenari con diversa percentuale di binari singoli."""
    print("\n" + "=" * 70)
    print("  ESPERIMENTO: Binari Singoli vs Doppi")
    print("=" * 70 + "\n")
    
    for single_ratio in [0.2, 0.5, 0.8]:
        print(f"\n📊 Scenario con {single_ratio*100:.0f}% binari singoli:")
        
        generator = RailwayNetworkGenerator(
            num_stations=10,
            num_tracks=15,
            single_track_ratio=single_ratio
        )
        
        scenario = generator.generate_scenario(
            num_trains=25,
            conflict_probability=0.4
        )
        
        conflicts = scenario['conflicts']
        trains = scenario['trains']
        
        print(f"  • Conflitti: {len(conflicts)}")
        print(f"  • Conflitti/treno: {len(conflicts)/len(trains):.2f}")
        
        # Conta conflitti critici su binari singoli
        critical = 0
        for t1_id, t2_id in conflicts:
            train = trains[t1_id]
            track = generator.tracks[train.current_track]
            if track.is_single_track:
                critical += 1
        
        print(f"  • Conflitti CRITICI (binario singolo): {critical}/{len(conflicts)}")


def experiment_train_density():
    """Testa come la densità di treni influisce sui conflitti."""
    print("\n" + "=" * 70)
    print("  ESPERIMENTO: Densità Treni")
    print("=" * 70 + "\n")
    
    generator = RailwayNetworkGenerator(
        num_stations=8,
        num_tracks=12,
        single_track_ratio=0.4
    )
    
    for num_trains in [10, 20, 30, 40]:
        scenario = generator.generate_scenario(
            num_trains=num_trains,
            conflict_probability=0.3
        )
        
        conflicts = scenario['conflicts']
        delayed = sum(1 for t in scenario['trains'] if t.is_delayed)
        
        print(f"\n🚂 {num_trains} treni:")
        print(f"  • Conflitti totali: {len(conflicts)}")
        print(f"  • In ritardo: {delayed} ({delayed/num_trains*100:.1f}%)")
        print(f"  • Densità: {num_trains/len(generator.tracks):.1f} treni/binario")


def experiment_priority_distribution():
    """Analizza come le priorità influenzano la risoluzione."""
    print("\n" + "=" * 70)
    print("  ESPERIMENTO: Distribuzione Priorità")
    print("=" * 70 + "\n")
    
    generator = RailwayNetworkGenerator(
        num_stations=8,
        num_tracks=12,
        single_track_ratio=0.5
    )
    
    scenario = generator.generate_scenario(
        num_trains=20,
        conflict_probability=0.5
    )
    
    trains = scenario['trains']
    conflicts = scenario['conflicts']
    
    # Analisi priorità
    priorities = [t.priority for t in trains]
    print(f"📈 Distribuzione priorità:")
    print(f"  • Media: {np.mean(priorities):.1f}")
    print(f"  • Min/Max: {min(priorities)}/{max(priorities)}")
    print(f"  • Std Dev: {np.std(priorities):.1f}")
    
    # Simula risoluzione
    print(f"\n⚖️ Simulazione risoluzione {len(conflicts)} conflitti:")
    
    total_delay_high_priority = 0
    total_delay_low_priority = 0
    
    for t1_id, t2_id in conflicts:
        t1 = trains[t1_id]
        t2 = trains[t2_id]
        
        if t1.priority < t2.priority:
            total_delay_low_priority += 10
        else:
            total_delay_high_priority += 10
    
    print(f"  • Ritardo treni alta priorità (>5): {total_delay_high_priority} min")
    print(f"  • Ritardo treni bassa priorità (≤5): {total_delay_low_priority} min")


def generate_custom_scenario():
    """Crea uno scenario personalizzato per capire meglio il sistema."""
    print("\n" + "=" * 70)
    print("  SCENARIO PERSONALIZZATO: Linea Milano-Bologna")
    print("=" * 70 + "\n")
    
    # Rete semplificata
    generator = RailwayNetworkGenerator(
        num_stations=5,  # Milano, Piacenza, Parma, Modena, Bologna
        num_tracks=4,    # Poche linee principali
        single_track_ratio=0.5  # Misto singolo/doppio
    )
    
    print("🗺️ Rete:")
    for i, station in enumerate(generator.stations):
        print(f"  {i+1}. {station.name}: {station.num_platforms} binari")
    
    print("\n🛤️ Binari:")
    for track in generator.tracks:
        tipo = "SINGOLO ⚠️" if track.is_single_track else "DOPPIO ✓"
        stazioni = f"{track.stations[0]} → {track.stations[1]}"
        print(f"  Binario {track.id}: {track.length_km:.0f}km ({tipo}) {stazioni}")
    
    # Scenario con traffico intenso
    scenario = generator.generate_scenario(
        num_trains=12,
        conflict_probability=0.7  # Alta probabilità per test
    )
    
    trains = scenario['trains']
    conflicts = scenario['conflicts']
    
    print(f"\n🚂 Situazione traffico:")
    print(f"  • Treni in circolazione: {len(trains)}")
    print(f"  • Conflitti rilevati: {len(conflicts)}")
    
    if conflicts:
        print(f"\n⚠️ CONFLITTI CRITICI:")
        for i, (t1_id, t2_id) in enumerate(conflicts[:3], 1):
            t1, t2 = trains[t1_id], trains[t2_id]
            track = generator.tracks[t1.current_track]
            
            print(f"\n  Conflitto {i}:")
            print(f"    Treno {t1_id}: {t1.velocity_kmh:.0f}km/h, priorità {t1.priority}")
            print(f"    Treno {t2_id}: {t2.velocity_kmh:.0f}km/h, priorità {t2.priority}")
            print(f"    Binario {track.id}: {track.length_km:.0f}km " + 
                  ("(SINGOLO - CRITICO!)" if track.is_single_track else "(doppio)"))
            
            dist = abs(t1.position_km - t2.position_km)
            print(f"    Distanza: {dist:.1f}km")


def main():
    print("\n" + "=" * 70)
    print("  🧪 RAILWAY AI SCHEDULER - ESPERIMENTI")
    print("=" * 70)
    
    # Esegui esperimenti
    experiment_single_vs_double_track()
    experiment_train_density()
    experiment_priority_distribution()
    generate_custom_scenario()
    
    # Riepilogo
    print("\n" + "=" * 70)
    print("  📚 OSSERVAZIONI")
    print("=" * 70 + "\n")
    
    print("💡 Lezioni apprese:")
    print("  1. Binari singoli → Più conflitti critici")
    print("  2. Alta densità treni → Più conflitti totali")
    print("  3. Priorità aiutano a minimizzare impatto complessivo")
    print("  4. Treni veloci su binari singoli = massimo rischio")
    
    print("\n🎯 Per il training della rete neurale:")
    print("  • Usa scenari variabili (20-40 treni)")
    print("  • Include mix binari singoli/doppi (30-50%)")
    print("  • Varia priorità per realismo")
    print("  • Genera molti esempi (1000+) per generalizzazione")
    
    print("\n" + "=" * 70 + "\n")


if __name__ == "__main__":
    main()
