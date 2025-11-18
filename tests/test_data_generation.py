"""
Test suite per i componenti Python del Railway AI Scheduler.
"""

import pytest
import numpy as np
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'python'))

from data.data_generator import RailwayNetworkGenerator, Track, Station, Train


class TestRailwayNetworkGenerator:
    """Test per il generatore di rete ferroviaria."""
    
    def test_initialization(self):
        """Test inizializzazione generatore."""
        generator = RailwayNetworkGenerator(num_stations=5, num_tracks=10)
        
        assert len(generator.stations) == 5
        assert len(generator.tracks) == 10
    
    def test_track_generation(self):
        """Test generazione binari."""
        generator = RailwayNetworkGenerator(num_stations=5, num_tracks=10, single_track_ratio=0.5)
        
        # Verifica che alcuni binari siano singoli
        single_tracks = [t for t in generator.tracks if t.is_single_track]
        assert len(single_tracks) > 0
        
        # Verifica lunghezze valide
        for track in generator.tracks:
            assert 5.0 <= track.length_km <= 100.0
            assert len(track.stations) == 2  # Binario connette 2 stazioni
    
    def test_scenario_generation(self):
        """Test generazione scenario completo."""
        generator = RailwayNetworkGenerator()
        scenario = generator.generate_scenario(num_trains=20)
        
        # Verifica struttura scenario
        assert 'network_state' in scenario
        assert 'train_states' in scenario
        assert 'conflict_matrix' in scenario
        assert 'trains' in scenario
        assert 'conflicts' in scenario
        
        # Verifica dimensioni
        assert len(scenario['trains']) == 20
        assert scenario['train_states'].shape == (50, 8)  # Max 50 treni, 8 features
    
    def test_conflict_detection(self):
        """Test rilevamento conflitti."""
        generator = RailwayNetworkGenerator(num_stations=3, num_tracks=2)
        
        # Crea scenario con alta probabilità di conflitti
        scenario = generator.generate_scenario(num_trains=10, conflict_probability=0.8)
        
        # Dovrebbero esserci conflitti
        assert len(scenario['conflicts']) > 0
        
        # Verifica struttura conflitti
        for t1_id, t2_id in scenario['conflicts']:
            assert 0 <= t1_id < len(scenario['trains'])
            assert 0 <= t2_id < len(scenario['trains'])
    
    def test_network_state_encoding(self):
        """Test encoding dello stato della rete."""
        generator = RailwayNetworkGenerator(num_stations=5, num_tracks=10)
        network_state = generator._encode_network_state()
        
        # Verifica tipo e dimensioni
        assert isinstance(network_state, np.ndarray)
        assert network_state.dtype == np.float32
        assert len(network_state) == 10 * 3 + 5 * 2  # tracks*3 + stations*2
    
    def test_train_state_encoding(self):
        """Test encoding stato treni."""
        generator = RailwayNetworkGenerator()
        
        trains = [
            Train(
                id=i,
                current_track=0,
                position_km=10.0 * i,
                velocity_kmh=100.0,
                scheduled_arrival=60.0,
                destination_station=1,
                priority=5,
                is_delayed=False,
                delay_minutes=0.0
            )
            for i in range(5)
        ]
        
        train_states = generator._encode_train_states(trains)
        
        # Verifica dimensioni
        assert train_states.shape == (50, 8)  # Max 50 treni, 8 features
        
        # Verifica normalizzazione (tutti valori tra 0 e 1)
        assert np.all(train_states >= 0.0)
        assert np.all(train_states <= 1.0)
    
    def test_conflict_matrix(self):
        """Test creazione matrice conflitti."""
        generator = RailwayNetworkGenerator()
        
        trains = [Train(id=i, current_track=0, position_km=0, velocity_kmh=100,
                       scheduled_arrival=60, destination_station=0, priority=5,
                       is_delayed=False, delay_minutes=0) for i in range(5)]
        
        conflicts = [(0, 1), (2, 3)]
        
        matrix = generator._create_conflict_matrix(trains, conflicts)
        
        # Verifica dimensioni
        assert matrix.shape == (50, 50)
        
        # Verifica simmetria
        assert matrix[0, 1] == 1.0
        assert matrix[1, 0] == 1.0
        assert matrix[2, 3] == 1.0
        assert matrix[3, 2] == 1.0
        
        # Verifica nessun conflitto su altri
        assert matrix[0, 2] == 0.0


class TestDatasetGeneration:
    """Test per generazione dataset."""
    
    def test_dataset_structure(self):
        """Test struttura dataset."""
        from data.data_generator import generate_training_dataset
        import tempfile
        import os
        
        # Genera piccolo dataset in file temporaneo
        with tempfile.NamedTemporaryFile(suffix='.npz', delete=False) as f:
            temp_path = f.name
        
        try:
            generate_training_dataset(num_samples=10, output_path=temp_path)
            
            # Carica e verifica
            data = np.load(temp_path)
            
            assert 'network_states' in data
            assert 'train_states' in data
            assert 'conflict_matrices' in data
            
            # Verifica dimensioni
            assert data['network_states'].shape[0] == 10
            assert data['train_states'].shape[0] == 10
            assert data['conflict_matrices'].shape[0] == 10
        
        finally:
            # Cleanup
            if os.path.exists(temp_path):
                os.remove(temp_path)


def test_imports():
    """Test che tutti i moduli siano importabili."""
    from models import scheduler_network
    from data import data_generator
    from training import train_model
    
    assert scheduler_network is not None
    assert data_generator is not None
    assert train_model is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
