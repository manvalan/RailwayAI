"""
Crea dataset con target realistici usando C++ solver.
I target sono soluzioni calcolate euristicamente dal C++ engine.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import railway_cpp as rc
from data.data_generator import RailwayNetworkGenerator
import numpy as np
from tqdm import tqdm


def solve_with_cpp_engine(scenario, generator):
    """
    Usa il C++ engine per calcolare una soluzione euristica.
    Questa diventerà il target per il supervised learning.
    """
    scheduler = rc.RailwayScheduler()
    
    # Inizializza rete
    tracks = []
    for track in generator.tracks:
        t = rc.Track()
        t.id = track.id
        t.length_km = track.length_km
        t.is_single_track = track.is_single_track
        t.capacity = track.capacity
        t.station_ids = list(track.stations)
        tracks.append(t)
    
    stations = []
    for station in generator.stations:
        s = rc.Station()
        s.id = station.id
        s.name = station.name
        s.num_platforms = station.num_platforms
        stations.append(s)
    
    scheduler.initialize_network(tracks, stations)
    
    # Aggiungi treni
    for train in scenario['trains']:
        t = rc.Train()
        t.id = train.id
        t.position_km = train.position_km
        t.velocity_kmh = train.velocity_kmh
        t.current_track = train.current_track
        t.destination_station = train.destination_station
        t.delay_minutes = train.delay_minutes
        t.priority = train.priority
        t.is_delayed = train.is_delayed
        scheduler.add_train(t)
    
    # Rileva e risolvi conflitti
    conflicts = scheduler.detect_conflicts()
    adjustments = scheduler.resolve_conflicts(conflicts)
    
    # Estrai aggiustamenti come target
    time_adjustments = np.zeros(len(scenario['trains']))
    track_assignments = np.zeros(len(scenario['trains']))
    
    for adj in adjustments:
        time_adjustments[adj.train_id] = adj.time_adjustment_minutes
        if adj.new_track_id >= 0:
            track_assignments[adj.train_id] = adj.new_track_id
    
    return {
        'time_adjustments': time_adjustments,
        'track_assignments': track_assignments,
        'num_conflicts': len(conflicts)
    }


def generate_supervised_dataset(num_samples=1000, output_path='../../data/supervised_training_data.npz'):
    """Genera dataset con target realistici."""
    
    print(f"\n{'='*70}")
    print(f"  🎯 GENERAZIONE DATASET SUPERVISED")
    print(f"{'='*70}\n")
    print(f"Target: {num_samples} samples con soluzioni C++ engine\n")
    
    all_network_states = []
    all_train_states = []
    all_conflict_matrices = []
    all_time_targets = []
    all_track_targets = []
    
    stats = {
        'total_conflicts': 0,
        'total_trains': 0,
        'scenarios_with_conflicts': 0
    }
    
    for i in tqdm(range(num_samples), desc="Generazione"):
        # Parametri variabili (garantisce almeno 30% binari singoli)
        num_stations = np.random.randint(5, 15)
        num_tracks = np.random.randint(8, 25)
        num_trains = np.random.randint(15, 50)
        single_ratio = np.random.uniform(0.3, 0.6)  # Min 30% per garantire almeno 1 singolo
        
        # Genera scenario (retry se fallisce per mancanza binari singoli)
        max_retries = 3
        for retry in range(max_retries):
            try:
                generator = RailwayNetworkGenerator(num_stations, num_tracks, single_ratio)
                scenario = generator.generate_scenario(num_trains, conflict_probability=0.4)
                break
            except IndexError:
                # Nessun binario singolo, aumenta il ratio
                single_ratio = min(0.8, single_ratio + 0.2)
                if retry == max_retries - 1:
                    # Fallback: usa più binari singoli
                    generator = RailwayNetworkGenerator(num_stations, num_tracks, 0.5)
                    scenario = generator.generate_scenario(num_trains, conflict_probability=0.3)
        
        # Calcola soluzione con C++
        solution = solve_with_cpp_engine(scenario, generator)
        
        # Estrai features (con padding a dimensione fissa)
        raw_network_state = generator._encode_network_state()
        network_state = np.zeros(80)  # Dimensione fissa
        network_state[:min(len(raw_network_state), 80)] = raw_network_state[:80]
        
        train_states = np.zeros((50, 8))
        for j, train in enumerate(scenario['trains'][:50]):
            train_states[j] = [
                train.position_km / 100.0,
                train.velocity_kmh / 200.0,
                train.delay_minutes / 60.0,
                train.priority / 10.0,
                train.current_track / float(num_tracks),
                train.destination_station / float(num_stations),
                0.0,  # time (sarà aggiornato durante simulazione)
                1.0 if train.is_delayed else 0.0
            ]
        
        conflict_matrix = np.zeros((50, 50))
        for t1_id, t2_id in scenario['conflicts']:
            if t1_id < 50 and t2_id < 50:
                conflict_matrix[t1_id, t2_id] = 1
                conflict_matrix[t2_id, t1_id] = 1
        
        # Padding targets
        time_targets = np.zeros(50)
        track_targets = np.zeros(50)
        time_targets[:len(solution['time_adjustments'])] = solution['time_adjustments']
        track_targets[:len(solution['track_assignments'])] = solution['track_assignments']
        
        # Accumula
        all_network_states.append(network_state)
        all_train_states.append(train_states)
        all_conflict_matrices.append(conflict_matrix)
        all_time_targets.append(time_targets)
        all_track_targets.append(track_targets)
        
        # Stats
        stats['total_conflicts'] += solution['num_conflicts']
        stats['total_trains'] += len(scenario['trains'])
        if solution['num_conflicts'] > 0:
            stats['scenarios_with_conflicts'] += 1
    
    # Converti in numpy arrays
    data = {
        'network_states': np.array(all_network_states),
        'train_states': np.array(all_train_states),
        'conflict_matrices': np.array(all_conflict_matrices),
        'time_targets': np.array(all_time_targets),
        'track_targets': np.array(all_track_targets)
    }
    
    # Salva
    np.savez_compressed(output_path, **data)
    
    # Report
    print(f"\n{'='*70}")
    print(f"  ✅ DATASET COMPLETATO")
    print(f"{'='*70}\n")
    print(f"📊 Statistiche:")
    print(f"  • Samples totali: {num_samples}")
    print(f"  • Scenari con conflitti: {stats['scenarios_with_conflicts']} ({stats['scenarios_with_conflicts']/num_samples*100:.1f}%)")
    print(f"  • Conflitti totali: {stats['total_conflicts']}")
    print(f"  • Media conflitti/scenario: {stats['total_conflicts']/num_samples:.2f}")
    print(f"  • Treni totali: {stats['total_trains']}")
    print(f"  • Media treni/scenario: {stats['total_trains']/num_samples:.1f}")
    print(f"\n💾 Salvato in: {output_path}")
    print(f"  • Dimensione: {data['network_states'].nbytes / 1024**2:.1f} MB")
    print(f"\n🎯 Prossimo passo: python training/train_supervised.py")
    print()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--samples', type=int, default=1000, help='Numero di samples da generare')
    parser.add_argument('--output', type=str, default='../../data/supervised_training_data.npz')
    args = parser.parse_args()
    
    generate_supervised_dataset(args.samples, args.output)
