"""
Benchmark del modello per valutare performance inference.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import torch
import time
import numpy as np
from models.scheduler_network import SchedulerNetwork
from data.data_generator import RailwayNetworkGenerator


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


def benchmark_inference(model, num_tests=100):
    """Benchmark velocità inference."""
    
    print("\n" + "="*70)
    print("  ⚡ BENCHMARK INFERENCE")
    print("="*70 + "\n")
    
    # Prepara input dummy
    batch_sizes = [1, 8, 16, 32]
    
    results = {}
    
    for batch_size in batch_sizes:
        network_state = torch.randn(batch_size, 80)
        train_states = torch.randn(batch_size, 50, 8)
        
        # Warmup
        with torch.no_grad():
            for _ in range(10):
                _ = model(network_state, train_states)
        
        # Benchmark
        times = []
        with torch.no_grad():
            for _ in range(num_tests):
                start = time.time()
                _ = model(network_state, train_states)
                end = time.time()
                times.append(end - start)
        
        avg_time = np.mean(times) * 1000  # ms
        std_time = np.std(times) * 1000
        min_time = np.min(times) * 1000
        max_time = np.max(times) * 1000
        
        throughput = batch_size / (avg_time / 1000)
        
        results[batch_size] = {
            'avg_ms': avg_time,
            'std_ms': std_time,
            'min_ms': min_time,
            'max_ms': max_time,
            'throughput': throughput
        }
        
        print(f"Batch {batch_size:2d}: {avg_time:6.2f}±{std_time:4.2f}ms  |  "
              f"Min: {min_time:5.2f}ms  Max: {max_time:5.2f}ms  |  "
              f"{throughput:5.1f} scenarios/sec")
    
    return results


def benchmark_memory():
    """Stima uso memoria del modello."""
    
    print("\n" + "="*70)
    print("  💾 ANALISI MEMORIA")
    print("="*70 + "\n")
    
    model, checkpoint = load_model()
    
    # Parametri
    num_params = sum(p.numel() for p in model.parameters())
    trainable_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
    
    # Stima memoria (FP32)
    param_memory_mb = (num_params * 4) / (1024**2)  # 4 bytes per param
    
    # Stima memoria attivazioni (batch=32, worst case)
    activation_memory_mb = (80 + 50*8 + 50*50) * 32 * 4 / (1024**2)
    
    total_memory_mb = param_memory_mb + activation_memory_mb
    
    print(f"Parametri totali: {num_params:,}")
    print(f"Parametri trainable: {trainable_params:,}")
    print(f"\nMemoria parametri: {param_memory_mb:.2f} MB")
    print(f"Memoria attivazioni (batch=32): {activation_memory_mb:.2f} MB")
    print(f"Memoria totale stimata: {total_memory_mb:.2f} MB")
    
    # Checkpoint size
    checkpoint_size_mb = Path('models/scheduler_supervised_best.pth').stat().st_size / (1024**2)
    print(f"\nDimensione checkpoint: {checkpoint_size_mb:.2f} MB")


def compare_with_cpp():
    """Confronta velocità ML vs C++."""
    
    print("\n" + "="*70)
    print("  🏁 CONFRONTO VELOCITÀ ML vs C++")
    print("="*70 + "\n")
    
    import railway_cpp as rc
    
    model, _ = load_model()
    
    # Genera scenario test
    generator = RailwayNetworkGenerator(10, 15, 0.4)
    scenario = generator.generate_scenario(30, 0.5)
    
    # Prepara input ML
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
    
    network_tensor = torch.FloatTensor(network_state).unsqueeze(0)
    train_tensor = torch.FloatTensor(train_states).unsqueeze(0)
    
    # Benchmark ML
    ml_times = []
    with torch.no_grad():
        for _ in range(100):
            start = time.time()
            _ = model(network_tensor, train_tensor)
            end = time.time()
            ml_times.append((end - start) * 1000)
    
    ml_avg = np.mean(ml_times)
    
    # Benchmark C++
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
    
    cpp_times = []
    for _ in range(100):
        start = time.time()
        conflicts = scheduler.detect_conflicts()
        _ = scheduler.resolve_conflicts(conflicts)
        end = time.time()
        cpp_times.append((end - start) * 1000)
    
    cpp_avg = np.mean(cpp_times)
    
    print(f"ML Inference:    {ml_avg:6.2f} ms")
    print(f"C++ Solver:      {cpp_avg:6.2f} ms")
    print(f"\nSpeedup ratio:   {ml_avg/cpp_avg:.2f}x")
    
    if cpp_avg < ml_avg:
        print(f"→ C++ è {ml_avg/cpp_avg:.1f}x più veloce per inference")
    else:
        print(f"→ ML è {cpp_avg/ml_avg:.1f}x più veloce per inference")


def main():
    print("\n" + "="*70)
    print("  📊 BENCHMARK MODELLO RAILWAY AI SCHEDULER")
    print("="*70)
    
    # Carica modello
    print("\n💾 Caricamento modello...")
    model, checkpoint = load_model()
    print(f"  • Epoca: {checkpoint['epoch']}")
    print(f"  • Val loss: {checkpoint['val_loss']:.4f}")
    
    # Benchmark
    benchmark_inference(model)
    benchmark_memory()
    compare_with_cpp()
    
    print("\n" + "="*70)
    print("  ✅ BENCHMARK COMPLETATO")
    print("="*70 + "\n")


if __name__ == "__main__":
    main()
