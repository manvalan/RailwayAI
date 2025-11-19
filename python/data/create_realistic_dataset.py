"""
Generate realistic railway dataset based on Italian and UK networks.

Uses real parameters from Italian (RFI) and UK (Network Rail) railways:
- Station distances
- Track configurations
- Train types and speeds
- Typical delays
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import numpy as np
import argparse
from tqdm import tqdm
from python.data.data_generator import RailwayNetworkGenerator


# Real-world railway parameters
ITALIAN_NETWORKS = {
    "milano-bologna": {
        "distance_km": 219,
        "stations": ["Milano Centrale", "Piacenza", "Parma", "Reggio Emilia", "Modena", "Bologna Centrale"],
        "avg_speed_kmh": 180,  # Alta Velocità
        "single_track_ratio": 0.1,  # Mostly double track
        "daily_trains": 120
    },
    "roma-napoli": {
        "distance_km": 225,
        "stations": ["Roma Termini", "Cassino", "Caserta", "Napoli Centrale"],
        "avg_speed_kmh": 170,
        "single_track_ratio": 0.15,
        "daily_trains": 100
    },
    "torino-milano": {
        "distance_km": 143,
        "stations": ["Torino Porta Nuova", "Novara", "Milano Centrale"],
        "avg_speed_kmh": 160,
        "single_track_ratio": 0.2,
        "daily_trains": 90
    },
    "firenze-roma": {
        "distance_km": 261,
        "stations": ["Firenze SMN", "Arezzo", "Orvieto", "Roma Termini"],
        "avg_speed_kmh": 175,
        "single_track_ratio": 0.12,
        "daily_trains": 85
    }
}

UK_NETWORKS = {
    "london-birmingham": {
        "distance_km": 160,
        "stations": ["London Euston", "Milton Keynes", "Birmingham New Street"],
        "avg_speed_kmh": 200,  # HS2/planned
        "single_track_ratio": 0.05,  # Very low
        "daily_trains": 150
    },
    "london-manchester": {
        "distance_km": 320,
        "stations": ["London Euston", "Crewe", "Stockport", "Manchester Piccadilly"],
        "avg_speed_kmh": 170,
        "single_track_ratio": 0.08,
        "daily_trains": 110
    },
    "edinburgh-glasgow": {
        "distance_km": 75,
        "stations": ["Edinburgh Waverley", "Falkirk", "Glasgow Queen Street"],
        "avg_speed_kmh": 140,
        "single_track_ratio": 0.15,
        "daily_trains": 200
    }
}


def generate_realistic_scenario(network_config, num_trains):
    """Generate scenario based on real network parameters"""
    
    num_stations = len(network_config["stations"])
    total_distance = network_config["distance_km"]
    
    # Create generator with realistic parameters
    generator = RailwayNetworkGenerator(
        num_stations=num_stations,
        num_tracks=num_stations * 2,  # ~2 tracks per station pair
        single_track_ratio=network_config["single_track_ratio"]
    )
    
    # Generate trains with realistic distribution
    trains = []
    for i in range(num_trains):
        # Realistic speed distribution (high speed, regional, freight)
        train_type = np.random.choice(
            ["high_speed", "regional", "freight"],
            p=[0.4, 0.5, 0.1]
        )
        
        if train_type == "high_speed":
            base_speed = network_config["avg_speed_kmh"]
            priority = np.random.randint(8, 11)
            delay_prob = 0.15
        elif train_type == "regional":
            base_speed = network_config["avg_speed_kmh"] * 0.7
            priority = np.random.randint(5, 8)
            delay_prob = 0.25
        else:  # freight
            base_speed = network_config["avg_speed_kmh"] * 0.5
            priority = np.random.randint(2, 5)
            delay_prob = 0.10
        
        # Random position along route
        position = np.random.uniform(0, total_distance)
        
        # Realistic delays (when they occur)
        is_delayed = np.random.random() < delay_prob
        if is_delayed:
            # Realistic delay distribution: most are small, few are large
            delay = np.random.choice(
                [2, 5, 10, 15, 30, 60],
                p=[0.4, 0.3, 0.15, 0.1, 0.04, 0.01]
            )
        else:
            delay = 0
        
        train = type('Train', (), {
            'id': i,
            'position_km': position,
            'velocity_kmh': base_speed + np.random.uniform(-10, 10),
            'current_track': np.random.randint(0, num_stations * 2),
            'destination_station': np.random.randint(0, num_stations),
            'delay_minutes': delay,
            'priority': priority,
            'is_delayed': is_delayed
        })()
        
        trains.append(train)
    
    return {
        'generator': generator,
        'trains': trains,
        'network_name': network_config.get('name', 'Unknown'),
        'metadata': {
            'distance_km': total_distance,
            'num_stations': num_stations,
            'avg_speed': network_config["avg_speed_kmh"],
            'single_track_ratio': network_config["single_track_ratio"]
        }
    }


def create_multi_country_dataset(samples_per_network=50, output_file='data/real_training_data.npz'):
    """Create dataset from multiple Italian and UK networks"""
    
    print("\n" + "="*70)
    print("  CREAZIONE DATASET REALISTICO ITALIA + UK")
    print("="*70 + "\n")
    
    all_network_states = []
    all_train_states = []
    all_conflict_matrices = []
    all_time_targets = []
    all_track_targets = []
    all_metadata = []
    
    # Combine Italian and UK networks
    all_networks = {**ITALIAN_NETWORKS, **UK_NETWORKS}
    
    total_samples = len(all_networks) * samples_per_network
    pbar = tqdm(total=total_samples, desc="Generazione scenari")
    
    for network_name, network_config in all_networks.items():
        network_config['name'] = network_name
        
        country = "🇮🇹 Italia" if network_name in ITALIAN_NETWORKS else "🇬🇧 UK"
        print(f"\n{country} - {network_name}")
        print(f"  Distanza: {network_config['distance_km']} km")
        print(f"  Stazioni: {len(network_config['stations'])}")
        print(f"  Treni/giorno: {network_config['daily_trains']}")
        
        for sample_idx in range(samples_per_network):
            # Variable number of trains per scenario
            num_trains = np.random.randint(
                network_config['daily_trains'] // 4,
                network_config['daily_trains'] // 2
            )
            
            scenario = generate_realistic_scenario(network_config, num_trains)
            generator = scenario['generator']
            
            # Encode network state
            raw_network_state = generator._encode_network_state()
            network_state = np.zeros(80)
            network_state[:min(len(raw_network_state), 80)] = raw_network_state[:80]
            
            # Encode train states (max 50 trains)
            train_states = np.zeros((50, 8))
            for j, train in enumerate(scenario['trains'][:50]):
                train_states[j] = [
                    train.position_km / 100.0,
                    train.velocity_kmh / 200.0,
                    train.delay_minutes / 60.0,
                    train.priority / 10.0,
                    train.current_track / 20.0,
                    train.destination_station / 10.0,
                    0.0,
                    1.0 if train.is_delayed else 0.0
                ]
            
            # Create conflict matrix
            conflict_matrix = np.zeros((50, 50))
            for i in range(min(len(scenario['trains']), 50)):
                for j in range(i+1, min(len(scenario['trains']), 50)):
                    t1, t2 = scenario['trains'][i], scenario['trains'][j]
                    if t1.current_track == t2.current_track:
                        distance = abs(t1.position_km - t2.position_km)
                        if distance < 10.0:
                            conflict_matrix[i, j] = 1.0
                            conflict_matrix[j, i] = 1.0
            
            # Simple targets (can be improved with C++ solver)
            time_targets = np.zeros(50)
            track_targets = np.zeros(50)
            
            for i, train in enumerate(scenario['trains'][:50]):
                if train.is_delayed:
                    time_targets[i] = -min(train.delay_minutes / 2.0, 10.0)
                    track_targets[i] = (train.current_track + 1) % (len(network_config['stations']) * 2)
            
            all_network_states.append(network_state)
            all_train_states.append(train_states)
            all_conflict_matrices.append(conflict_matrix)
            all_time_targets.append(time_targets)
            all_track_targets.append(track_targets)
            all_metadata.append({
                'network': network_name,
                'country': 'IT' if network_name in ITALIAN_NETWORKS else 'UK',
                'num_trains': len(scenario['trains']),
                'num_delayed': sum(1 for t in scenario['trains'] if t.is_delayed)
            })
            
            pbar.update(1)
    
    pbar.close()
    
    # Convert to numpy arrays
    network_states = np.array(all_network_states)
    train_states = np.array(all_train_states)
    conflict_matrices = np.array(all_conflict_matrices)
    time_targets = np.array(all_time_targets)
    track_targets = np.array(all_track_targets)
    
    # Save to file
    np.savez_compressed(
        output_file,
        network_states=network_states,
        train_states=train_states,
        conflict_matrices=conflict_matrices,
        time_targets=time_targets,
        track_targets=track_targets,
        metadata=all_metadata
    )
    
    # Statistics
    total_trains = sum(m['num_trains'] for m in all_metadata)
    total_delayed = sum(m['num_delayed'] for m in all_metadata)
    total_conflicts = np.sum(conflict_matrices) / 2
    
    italian_samples = sum(1 for m in all_metadata if m['country'] == 'IT')
    uk_samples = sum(1 for m in all_metadata if m['country'] == 'UK')
    
    print("\n" + "="*70)
    print("  STATISTICHE DATASET")
    print("="*70)
    print(f"\nCampioni totali: {len(all_metadata)}")
    print(f"  🇮🇹 Italiani: {italian_samples}")
    print(f"  🇬🇧 UK: {uk_samples}")
    print(f"\nTreni totali: {total_trains}")
    print(f"  Ritardati: {total_delayed} ({total_delayed/total_trains*100:.1f}%)")
    print(f"  Puntuali: {total_trains - total_delayed} ({(1-total_delayed/total_trains)*100:.1f}%)")
    print(f"\nConflitti totali: {int(total_conflicts)}")
    print(f"  Media per scenario: {total_conflicts/len(all_metadata):.1f}")
    print(f"\nFile salvato: {output_file}")
    print(f"Dimensione: {Path(output_file).stat().st_size / 1024**2:.2f} MB")
    print("\n" + "="*70 + "\n")


def main():
    parser = argparse.ArgumentParser(description='Generate realistic railway dataset')
    parser.add_argument('--samples', type=int, default=100,
                       help='Samples per network (default: 100)')
    parser.add_argument('--output', type=str, default='data/real_training_data.npz',
                       help='Output file path')
    
    args = parser.parse_args()
    
    create_multi_country_dataset(
        samples_per_network=args.samples,
        output_file=args.output
    )


if __name__ == "__main__":
    main()
