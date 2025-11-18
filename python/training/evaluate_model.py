"""
Valuta il modello addestrato su scenari di test.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import torch
import numpy as np
from models.scheduler_network import SchedulerNetwork
from data.data_generator import RailwayNetworkGenerator
import railway_cpp as rc


def load_model(checkpoint_path='models/scheduler_supervised_best.pth'):
    """Carica il modello addestrato."""
    checkpoint = torch.load(checkpoint_path, map_location='cpu')
    config = checkpoint['config']
    
    model = SchedulerNetwork(
        input_dim=config['input_dim'],
        hidden_dim=config['hidden_dim'],
        num_trains=config['num_trains'],
        num_tracks=config['num_tracks'],
        num_stations=config['num_stations']
    )
    
    model.load_state_dict(checkpoint['model_state_dict'])
    model.eval()
    
    return model, checkpoint


def evaluate_on_scenario(model, scenario, generator):
    """Valuta il modello su uno scenario."""
    
    # Prepara input
    raw_network_state = generator._encode_network_state()
    network_state = np.zeros(80)
    network_state[:min(len(raw_network_state), 80)] = raw_network_state[:80]
    
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
    
    # Converti a tensors
    network_state_tensor = torch.FloatTensor(network_state).unsqueeze(0)
    train_states_tensor = torch.FloatTensor(train_states).unsqueeze(0)
    
    # Predizione
    with torch.no_grad():
        outputs = model(network_state_tensor, train_states_tensor)
        if isinstance(outputs, dict):
            time_pred = outputs['time_adjustments'].squeeze().numpy()
        else:
            time_pred = outputs[0].squeeze().numpy()
    
    return time_pred


def compare_with_cpp_solver(model, num_tests=10):
    """Confronta predizioni ML vs solver C++."""
    
    print("\n" + "="*70)
    print("  📊 VALUTAZIONE MODELLO vs C++ SOLVER")
    print("="*70 + "\n")
    
    results = {
        'ml_better': 0,
        'cpp_better': 0,
        'similar': 0,
        'ml_adjustments': [],
        'cpp_adjustments': []
    }
    
    for i in range(num_tests):
        # Genera scenario
        num_stations = np.random.randint(5, 12)
        num_tracks = np.random.randint(8, 20)
        num_trains = np.random.randint(15, 40)
        
        generator = RailwayNetworkGenerator(num_stations, num_tracks, 0.4)
        scenario = generator.generate_scenario(num_trains, 0.4)
        
        # Predizione ML
        ml_adjustments = evaluate_on_scenario(model, scenario, generator)
        ml_total = np.abs(ml_adjustments[:len(scenario['trains'])]).sum()
        
        # Soluzione C++
        scheduler = rc.RailwayScheduler()
        
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
        
        conflicts = scheduler.detect_conflicts()
        adjustments = scheduler.resolve_conflicts(conflicts)
        
        cpp_total = sum(abs(adj.time_adjustment_minutes) for adj in adjustments)
        
        # Confronta
        if ml_total < cpp_total * 0.9:
            results['ml_better'] += 1
        elif cpp_total < ml_total * 0.9:
            results['cpp_better'] += 1
        else:
            results['similar'] += 1
        
        results['ml_adjustments'].append(ml_total)
        results['cpp_adjustments'].append(cpp_total)
        
        print(f"Test {i+1:2d}: ML={ml_total:6.1f}min | C++={cpp_total:6.1f}min | " + 
              f"Conflitti={len(conflicts)} | " + 
              ("✅ ML" if ml_total < cpp_total else "⚙️ C++" if cpp_total < ml_total else "🤝 ="))
    
    # Report finale
    print("\n" + "="*70)
    print("  📈 RISULTATI FINALI")
    print("="*70 + "\n")
    
    print(f"Confronto su {num_tests} scenari casuali:\n")
    print(f"  🎯 ML migliore: {results['ml_better']} ({results['ml_better']/num_tests*100:.0f}%)")
    print(f"  ⚙️  C++ migliore: {results['cpp_better']} ({results['cpp_better']/num_tests*100:.0f}%)")
    print(f"  🤝 Simili: {results['similar']} ({results['similar']/num_tests*100:.0f}%)")
    
    ml_avg = np.mean(results['ml_adjustments'])
    cpp_avg = np.mean(results['cpp_adjustments'])
    
    print(f"\n📊 Ritardi medi:")
    print(f"  • ML Model: {ml_avg:.1f} minuti")
    print(f"  • C++ Solver: {cpp_avg:.1f} minuti")
    print(f"  • Differenza: {abs(ml_avg - cpp_avg):.1f} minuti ({abs(ml_avg - cpp_avg)/cpp_avg*100:.1f}%)")
    
    if ml_avg < cpp_avg:
        print(f"\n🏆 **ML Model è {(cpp_avg - ml_avg)/cpp_avg*100:.1f}% più efficiente!**")
    else:
        print(f"\n💡 C++ solver ancora migliore di {(ml_avg - cpp_avg)/cpp_avg*100:.1f}%")
        print("   → Considera più training o fine-tuning")
    
    print()


def main():
    print("\n" + "="*70)
    print("  🧪 VALUTAZIONE MODELLO ADDESTRATO")
    print("="*70 + "\n")
    
    # Carica modello
    print("💾 Caricamento modello...")
    model, checkpoint = load_model()
    
    print(f"  • Epoca: {checkpoint['epoch']}")
    print(f"  • Train loss: {checkpoint['train_loss']:.4f}")
    print(f"  • Val loss: {checkpoint['val_loss']:.4f}")
    print(f"  • Parametri: {sum(p.numel() for p in model.parameters()):,}")
    
    # Valutazione comparativa
    compare_with_cpp_solver(model, num_tests=20)
    
    print("✅ Valutazione completata!")
    print()


if __name__ == "__main__":
    main()
