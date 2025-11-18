"""
Generatore di dati sintetici per training della rete neurale.
Simula scenari realistici di rete ferroviaria.
"""

import numpy as np
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
import random


@dataclass
class Track:
    """Rappresenta un binario."""
    id: int
    length_km: float
    is_single_track: bool
    capacity: int  # Numero massimo treni simultanei
    stations: List[int]  # IDs delle stazioni collegate


@dataclass
class Station:
    """Rappresenta una stazione."""
    id: int
    name: str
    num_platforms: int
    connected_tracks: List[int]


@dataclass
class Train:
    """Rappresenta un treno."""
    id: int
    current_track: int
    position_km: float
    velocity_kmh: float
    scheduled_arrival: float  # minuti da ora
    destination_station: int
    priority: int  # 0-10
    is_delayed: bool
    delay_minutes: float


class RailwayNetworkGenerator:
    """
    Genera configurazioni di rete ferroviaria realistiche.
    """
    
    def __init__(self, 
                 num_stations: int = 10,
                 num_tracks: int = 20,
                 single_track_ratio: float = 0.3):
        self.num_stations = num_stations
        self.num_tracks = num_tracks
        self.single_track_ratio = single_track_ratio
        
        self.stations = self._generate_stations()
        self.tracks = self._generate_tracks()
        
    def _generate_stations(self) -> List[Station]:
        """Genera stazioni con capacità variabili."""
        stations = []
        station_names = [f"Stazione_{i}" for i in range(self.num_stations)]
        
        for i in range(self.num_stations):
            # Stazioni più grandi hanno più binari
            is_major = random.random() < 0.3
            num_platforms = random.randint(4, 12) if is_major else random.randint(2, 4)
            
            stations.append(Station(
                id=i,
                name=station_names[i],
                num_platforms=num_platforms,
                connected_tracks=[]
            ))
        
        return stations
    
    def _generate_tracks(self) -> List[Track]:
        """Genera binari che connettono le stazioni."""
        tracks = []
        
        for i in range(self.num_tracks):
            is_single = random.random() < self.single_track_ratio
            length = random.uniform(5, 100)  # km
            
            # Connetti 2 stazioni random
            station_ids = random.sample(range(self.num_stations), 2)
            
            track = Track(
                id=i,
                length_km=length,
                is_single_track=is_single,
                capacity=1 if is_single else random.randint(2, 4),
                stations=station_ids
            )
            
            tracks.append(track)
            
            # Aggiorna connessioni stazioni
            for sid in station_ids:
                self.stations[sid].connected_tracks.append(i)
        
        return tracks
    
    def generate_scenario(self, 
                         num_trains: int = 30,
                         conflict_probability: float = 0.3) -> Dict:
        """
        Genera uno scenario di traffico ferroviario.
        
        Args:
            num_trains: Numero di treni attivi
            conflict_probability: Probabilità di conflitti intenzionali
            
        Returns:
            Dict con network_state, train_states, conflicts
        """
        trains = []
        
        for i in range(num_trains):
            # Seleziona track random
            track = random.choice(self.tracks)
            position = random.uniform(0, track.length_km)
            velocity = random.uniform(60, 200)  # km/h
            
            # Crea possibili conflitti
            is_delayed = random.random() < 0.2
            delay = random.uniform(5, 45) if is_delayed else 0
            
            # Tempo di arrivo stimato
            remaining_distance = track.length_km - position
            arrival_time = (remaining_distance / velocity) * 60 + delay  # minuti
            
            train = Train(
                id=i,
                current_track=track.id,
                position_km=position,
                velocity_kmh=velocity,
                scheduled_arrival=arrival_time,
                destination_station=track.stations[-1],
                priority=random.randint(1, 10),
                is_delayed=is_delayed,
                delay_minutes=delay
            )
            trains.append(train)
        
        # Rilevamento conflitti
        conflicts = self._detect_conflicts(trains)
        
        # Se vogliamo più conflitti, forziamoli
        if len(conflicts) < num_trains * conflict_probability:
            trains = self._inject_conflicts(trains, int(num_trains * conflict_probability))
            conflicts = self._detect_conflicts(trains)
        
        # Converti in formato training
        network_state = self._encode_network_state()
        train_states = self._encode_train_states(trains)
        conflict_matrix = self._create_conflict_matrix(trains, conflicts)
        
        return {
            'network_state': network_state,
            'train_states': train_states,
            'conflict_matrix': conflict_matrix,
            'trains': trains,
            'conflicts': conflicts
        }
    
    def _detect_conflicts(self, trains: List[Train]) -> List[Tuple[int, int]]:
        """
        Rileva conflitti tra treni sullo stesso binario.
        
        Returns:
            Lista di tuple (train_id1, train_id2) in conflitto
        """
        conflicts = []
        
        # Raggruppa treni per binario
        trains_by_track = {}
        for train in trains:
            if train.current_track not in trains_by_track:
                trains_by_track[train.current_track] = []
            trains_by_track[train.current_track].append(train)
        
        # Controlla conflitti su ogni binario
        for track_id, track_trains in trains_by_track.items():
            track = self.tracks[track_id]
            
            if track.is_single_track:
                # Binario singolo: controlla direzioni opposte
                for i, t1 in enumerate(track_trains):
                    for t2 in track_trains[i+1:]:
                        if self._trains_will_collide(t1, t2, track):
                            conflicts.append((t1.id, t2.id))
            
            else:
                # Binario multiplo: controlla se superano capacità
                if len(track_trains) > track.capacity:
                    # Trova treni troppo vicini
                    sorted_trains = sorted(track_trains, key=lambda t: t.position_km)
                    for i in range(len(sorted_trains) - 1):
                        if sorted_trains[i+1].position_km - sorted_trains[i].position_km < 2.0:  # < 2km
                            conflicts.append((sorted_trains[i].id, sorted_trains[i+1].id))
        
        return conflicts
    
    def _trains_will_collide(self, t1: Train, t2: Train, track: Track) -> bool:
        """Verifica se due treni su binario singolo sono in rotta di collisione."""
        # Semplificazione: considera collisione se:
        # 1. Viaggiano in direzioni opposte
        # 2. Sono a meno di tempo_minimo di distanza
        
        # Determina direzione (verso inizio o fine del binario)
        t1_to_end = t1.position_km > track.length_km / 2
        t2_to_end = t2.position_km > track.length_km / 2
        
        if t1_to_end == t2_to_end:
            # Stessa direzione, no collisione diretta
            return False
        
        # Direzioni opposte: calcola tempo di incontro
        relative_velocity = t1.velocity_kmh + t2.velocity_kmh
        distance = abs(t1.position_km - t2.position_km)
        time_to_meet = (distance / relative_velocity) * 60  # minuti
        
        # Conflitto se si incontrano entro 5 minuti
        return time_to_meet < 5
    
    def _inject_conflicts(self, trains: List[Train], target_conflicts: int) -> List[Train]:
        """Inietta conflitti artificiali modificando posizioni/velocità."""
        conflicts_added = 0
        
        while conflicts_added < target_conflicts and len(trains) >= 2:
            # Seleziona due treni random
            t1, t2 = random.sample(trains, 2)
            
            # Mettili sullo stesso binario
            track = random.choice([t for t in self.tracks if t.is_single_track])
            t1.current_track = track.id
            t2.current_track = track.id
            
            # Posizionali in modo da creare conflitto
            t1.position_km = random.uniform(0, track.length_km * 0.4)
            t2.position_km = random.uniform(track.length_km * 0.6, track.length_km)
            
            # Velocità che causano incontro
            t1.velocity_kmh = random.uniform(80, 120)
            t2.velocity_kmh = random.uniform(80, 120)
            
            conflicts_added += 1
        
        return trains
    
    def _encode_network_state(self) -> np.ndarray:
        """
        Codifica lo stato della rete in un vettore.
        
        Returns:
            Array [num_tracks + num_stations]
        """
        track_features = []
        for track in self.tracks:
            # Feature: [is_single, capacity_normalized, length_normalized]
            track_features.extend([
                1.0 if track.is_single_track else 0.0,
                track.capacity / 4.0,
                track.length_km / 100.0
            ])
        
        station_features = []
        for station in self.stations:
            # Feature: [num_platforms_normalized, num_connections]
            station_features.extend([
                station.num_platforms / 12.0,
                len(station.connected_tracks) / self.num_tracks
            ])
        
        # Padding o troncamento
        target_tracks = self.num_tracks * 3
        target_stations = self.num_stations * 2
        
        track_features = (track_features + [0] * target_tracks)[:target_tracks]
        station_features = (station_features + [0] * target_stations)[:target_stations]
        
        return np.array(track_features + station_features, dtype=np.float32)
    
    def _encode_train_states(self, trains: List[Train]) -> np.ndarray:
        """
        Codifica lo stato dei treni.
        
        Returns:
            Array [num_trains, 8]
        """
        max_trains = 50
        train_matrix = np.zeros((max_trains, 8), dtype=np.float32)
        
        for i, train in enumerate(trains[:max_trains]):
            train_matrix[i] = [
                train.position_km / 100.0,  # Normalizzato
                train.velocity_kmh / 200.0,
                train.delay_minutes / 60.0,
                train.priority / 10.0,
                train.current_track / self.num_tracks,
                train.destination_station / self.num_stations,
                train.scheduled_arrival / 120.0,  # Normalizzato su 2 ore
                1.0 if train.is_delayed else 0.0
            ]
        
        return train_matrix
    
    def _create_conflict_matrix(self, 
                               trains: List[Train], 
                               conflicts: List[Tuple[int, int]]) -> np.ndarray:
        """
        Crea matrice binaria dei conflitti.
        
        Returns:
            Array [num_trains, num_trains] con 1 dove c'è conflitto
        """
        max_trains = 50
        matrix = np.zeros((max_trains, max_trains), dtype=np.float32)
        
        for t1_id, t2_id in conflicts:
            if t1_id < max_trains and t2_id < max_trains:
                matrix[t1_id, t2_id] = 1.0
                matrix[t2_id, t1_id] = 1.0
        
        return matrix


def generate_training_dataset(num_samples: int = 1000,
                              output_path: str = "data/training_data.npz") -> None:
    """
    Genera un dataset completo per il training.
    
    Args:
        num_samples: Numero di scenari da generare
        output_path: Percorso dove salvare il dataset
    """
    generator = RailwayNetworkGenerator()
    
    network_states = []
    train_states = []
    conflict_matrices = []
    
    print(f"Generazione di {num_samples} scenari...")
    
    for i in range(num_samples):
        if (i + 1) % 100 == 0:
            print(f"  Generati {i + 1}/{num_samples} scenari")
        
        scenario = generator.generate_scenario(
            num_trains=random.randint(20, 40),
            conflict_probability=random.uniform(0.2, 0.5)
        )
        
        network_states.append(scenario['network_state'])
        train_states.append(scenario['train_states'])
        conflict_matrices.append(scenario['conflict_matrix'])
    
    # Salva dataset
    np.savez_compressed(
        output_path,
        network_states=np.array(network_states),
        train_states=np.array(train_states),
        conflict_matrices=np.array(conflict_matrices)
    )
    
    print(f"Dataset salvato in: {output_path}")
    print(f"  Network states shape: {np.array(network_states).shape}")
    print(f"  Train states shape: {np.array(train_states).shape}")
    print(f"  Conflict matrices shape: {np.array(conflict_matrices).shape}")


if __name__ == "__main__":
    # Genera dataset di esempio
    generate_training_dataset(num_samples=1000, output_path="../data/training_data.npz")
    generate_training_dataset(num_samples=200, output_path="../data/validation_data.npz")
