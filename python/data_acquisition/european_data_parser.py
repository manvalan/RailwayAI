"""
Parser unificato per dati GTFS multi-paese europeo.

Integra dati da:
- Francia (SNCF TER/TGV)
- Paesi Bassi (NS)
- Germania (DB) - se disponibile
- Svizzera (SBB) - se disponibile
- Italia (RFI/Trenitalia) - già esistente

Output: Dataset unificato per training rete neurale
"""

import logging
import pandas as pd
import numpy as np
import zipfile
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
from gtfs_cache_manager import GTFSCache

logger = logging.getLogger(__name__)


@dataclass
class RailwayRoute:
    """Rappresenta una rotta ferroviaria."""
    route_id: str
    country: str
    route_name: str
    route_type: int  # 2=treno regionale, 100=treni alta velocità, etc
    avg_speed_kmh: float
    stops: List[str]
    departure_times: List[str]
    travel_times_min: List[float]


class EuropeanGTFSParser:
    """
    Parser unificato per GTFS europei multi-paese.
    Normalizza dati da diverse fonti in formato comune.
    Usa cache compresso per file grandi.
    """
    
    def __init__(self, data_dir: str = "data/european", use_cache: bool = True):
        self.data_dir = Path(data_dir)
        self.routes = []
        self.stops = {}
        self.country_stats = {}
        self.use_cache = use_cache
        self.cache_manager = GTFSCache() if use_cache else None
        
    def parse_country(self, country_code: str) -> bool:
        """
        Parsa GTFS per un singolo paese.
        Usa cache compresso se disponibile per performance.
        
        Args:
            country_code: es. 'france_sncf', 'netherlands_ns'
            
        Returns:
            True se parsing riuscito
        """
        gtfs_file = self.data_dir / f"{country_code}_gtfs.zip"
        
        if not gtfs_file.exists():
            logger.warning(f"File GTFS non trovato: {gtfs_file}")
            return False
        
        logger.info(f"📖 Parsing {country_code}...")
        
        # Usa cache se abilitato
        if self.use_cache and self.cache_manager:
            cached_data = self.cache_manager.get_or_create_cache(country_code, gtfs_file)
            if cached_data:
                return self._parse_from_cache(country_code, cached_data)
        
        # Fallback: parsing diretto da ZIP
        try:
            with zipfile.ZipFile(gtfs_file, 'r') as zf:
                # Leggi file GTFS richiesti
                stops_df = pd.read_csv(zf.open('stops.txt'))
                routes_df = pd.read_csv(zf.open('routes.txt'))
                trips_df = pd.read_csv(zf.open('trips.txt'))
                stop_times_df = pd.read_csv(zf.open('stop_times.txt'))
                
                # Filtra solo treni (route_type 2=rail, 100-199=high speed rail)
                train_routes = routes_df[
                    (routes_df['route_type'] == 2) | 
                    ((routes_df['route_type'] >= 100) & (routes_df['route_type'] < 200))
                ]
                
                logger.info(f"  Fermate: {len(stops_df)}")
                logger.info(f"  Rotte treni: {len(train_routes)}/{len(routes_df)}")
                logger.info(f"  Corse: {len(trips_df)}")
                
                # Processa campione di rotte (prime 1000 per performance)
                sample_size = min(1000, len(train_routes))
                for idx, route in train_routes.head(sample_size).iterrows():
                    route_trips = trips_df[trips_df['route_id'] == route['route_id']]
                    
                    if len(route_trips) == 0:
                        continue
                    
                    # Prendi prima corsa come rappresentativa
                    trip = route_trips.iloc[0]
                    trip_stops = stop_times_df[
                        stop_times_df['trip_id'] == trip['trip_id']
                    ].sort_values('stop_sequence')
                    
                    if len(trip_stops) < 2:
                        continue
                    
                    # Estrai informazioni rotta
                    stop_ids = trip_stops['stop_id'].tolist()
                    departure_times = trip_stops['departure_time'].tolist()
                    
                    # Calcola tempi di viaggio
                    travel_times = []
                    for i in range(len(trip_stops) - 1):
                        dep = trip_stops.iloc[i]['departure_time']
                        arr = trip_stops.iloc[i + 1]['arrival_time']
                        
                        # Parse time (HH:MM:SS, può essere >24h)
                        try:
                            dep_mins = self._time_to_minutes(dep)
                            arr_mins = self._time_to_minutes(arr)
                            travel_time = arr_mins - dep_mins
                            if travel_time < 0:
                                travel_time += 24 * 60  # Correggi giorno successivo
                            travel_times.append(travel_time)
                        except:
                            travel_times.append(0.0)
                    
                    # Calcola velocità media (stima distanza da coordinate)
                    avg_speed = self._estimate_avg_speed(trip_stops, stops_df)
                    
                    # Crea oggetto rotta
                    railway_route = RailwayRoute(
                        route_id=route['route_id'],
                        country=country_code,
                        route_name=route.get('route_long_name', route.get('route_short_name', 'Unknown')),
                        route_type=route['route_type'],
                        avg_speed_kmh=avg_speed,
                        stops=stop_ids,
                        departure_times=departure_times,
                        travel_times_min=travel_times
                    )
                    
                    self.routes.append(railway_route)
                
                # Salva fermate
                for _, stop in stops_df.iterrows():
                    self.stops[stop['stop_id']] = {
                        'name': stop['stop_name'],
                        'lat': stop.get('stop_lat', 0.0),
                        'lon': stop.get('stop_lon', 0.0),
                        'country': country_code
                    }
                
                # Statistiche paese
                self.country_stats[country_code] = {
                    'routes_parsed': len([r for r in self.routes if r.country == country_code]),
                    'total_stops': len(stops_df),
                    'total_trips': len(trips_df),
                    'avg_route_speed': np.mean([r.avg_speed_kmh for r in self.routes if r.country == country_code])
                }
                
                logger.info(f"✓ {country_code}: {self.country_stats[country_code]['routes_parsed']} rotte parsate")
                
                return True
                
        except Exception as e:
            logger.error(f"Errore parsing {country_code}: {e}")
            return False
    
    def _parse_from_cache(self, country_code: str, cached_data: Dict) -> bool:
        """
        Parsing rapido da cache compresso.
        
        Args:
            country_code: Codice paese
            cached_data: Dati dal cache manager
            
        Returns:
            True se successo
        """
        try:
            logger.info(f"  ⚡ Usando cache compresso (molto più veloce!)")
            
            # Ricostruisci stops
            if 'stops' in cached_data:
                stops_data = cached_data['stops']
                for i, stop_id in enumerate(stops_data['stop_ids']):
                    self.stops[stop_id] = {
                        'name': stops_data['stop_names'][i] if i < len(stops_data['stop_names']) else 'Unknown',
                        'lat': stops_data['stop_lats'][i] if i < len(stops_data['stop_lats']) else 0.0,
                        'lon': stops_data['stop_lons'][i] if i < len(stops_data['stop_lons']) else 0.0,
                        'country': country_code
                    }
            
            # Ricostruisci routes
            if 'routes' in cached_data and 'trip_patterns' in cached_data:
                routes_data = cached_data['routes']
                patterns = cached_data['trip_patterns']
                
                for i, route_id in enumerate(routes_data['route_ids'][:len(patterns)]):
                    pattern = patterns[i] if i < len(patterns) else patterns[0]
                    
                    # Stima velocità (placeholder, potremmo calcolarla meglio)
                    avg_speed = 100.0  # Default
                    
                    railway_route = RailwayRoute(
                        route_id=route_id,
                        country=country_code,
                        route_name=routes_data['route_names'][i] if i < len(routes_data['route_names']) else 'Unknown',
                        route_type=routes_data['route_types'][i] if i < len(routes_data['route_types']) else 2,
                        avg_speed_kmh=avg_speed,
                        stops=pattern['stop_sequence'],
                        departure_times=pattern['departure_times'],
                        travel_times_min=[5.0] * (len(pattern['stop_sequence']) - 1)  # Placeholder
                    )
                    
                    self.routes.append(railway_route)
            
            # Statistiche
            stats = cached_data.get('statistics', {})
            self.country_stats[country_code] = {
                'routes_parsed': len([r for r in self.routes if r.country == country_code]),
                'total_stops': stats.get('total_stops', 0),
                'total_trips': stats.get('sampled_trips', 0),
                'avg_route_speed': 100.0  # Placeholder
            }
            
            logger.info(f"✓ {country_code}: {self.country_stats[country_code]['routes_parsed']} rotte da cache")
            
            return True
            
        except Exception as e:
            logger.error(f"Errore parsing cache: {e}")
            return False
    
    def parse_all_available(self) -> int:
        """
        Parsa tutti i GTFS disponibili nella directory.
        
        Returns:
            Numero di paesi parsati con successo
        """
        gtfs_files = list(self.data_dir.glob("*_gtfs.zip"))
        
        logger.info("=" * 70)
        logger.info(f"📖 PARSING DATI GTFS EUROPEI - {len(gtfs_files)} file disponibili")
        logger.info("=" * 70)
        
        success_count = 0
        
        for gtfs_file in gtfs_files:
            # Estrai country code dal nome file
            country_code = gtfs_file.stem.replace('_gtfs', '')
            
            if self.parse_country(country_code):
                success_count += 1
        
        logger.info("\n" + "=" * 70)
        logger.info(f"✓ PARSING COMPLETATO: {success_count}/{len(gtfs_files)} paesi")
        logger.info("=" * 70)
        
        # Mostra statistiche aggregate
        total_routes = len(self.routes)
        total_stops = len(self.stops)
        
        logger.info(f"\n📊 STATISTICHE AGGREGATE:")
        logger.info(f"   Rotte totali: {total_routes}")
        logger.info(f"   Fermate totali: {total_stops}")
        logger.info(f"   Paesi: {', '.join(self.country_stats.keys())}")
        
        for country, stats in self.country_stats.items():
            logger.info(f"\n   {country.upper()}:")
            logger.info(f"     Rotte: {stats['routes_parsed']}")
            logger.info(f"     Fermate: {stats['total_stops']}")
            logger.info(f"     Velocità media: {stats['avg_route_speed']:.1f} km/h")
        
        return success_count
    
    def export_for_training(self, output_file: str = "data/european_training_data.npz"):
        """
        Esporta dati in formato compatibile con training rete neurale.
        
        Formato output:
        - route_features: [num_routes, feature_dim] array di features rotte
        - network_graph: rappresentazione grafo rete ferroviaria
        - conflict_scenarios: scenari di conflitto per training
        """
        if not self.routes:
            logger.error("Nessuna rotta disponibile. Esegui parse_all_available() prima.")
            return False
        
        logger.info(f"\n📦 Esportazione dataset per training...")
        
        # Feature encoding per ogni rotta
        route_features = []
        route_metadata = []
        
        for route in self.routes:
            # Features numeriche
            features = [
                route.avg_speed_kmh / 300.0,  # Normalizzato (max 300 km/h)
                len(route.stops) / 50.0,  # Normalizzato (max 50 fermate)
                np.mean(route.travel_times_min) / 120.0,  # Tempo medio normalizzato
                float(route.route_type == 2),  # Is regional
                float(route.route_type >= 100),  # Is high-speed
            ]
            
            route_features.append(features)
            
            # Metadata per interpretazione
            route_metadata.append({
                'route_id': route.route_id,
                'country': route.country,
                'name': route.route_name,
                'num_stops': len(route.stops)
            })
        
        route_features = np.array(route_features, dtype=np.float32)
        
        # Crea matrice adiacenza grafo (fermate connesse)
        stop_to_idx = {stop_id: idx for idx, stop_id in enumerate(self.stops.keys())}
        num_stops = len(self.stops)
        adjacency_matrix = np.zeros((num_stops, num_stops), dtype=np.float32)
        
        for route in self.routes:
            for i in range(len(route.stops) - 1):
                stop1_idx = stop_to_idx.get(route.stops[i])
                stop2_idx = stop_to_idx.get(route.stops[i + 1])
                
                if stop1_idx is not None and stop2_idx is not None:
                    # Peso = tempo di viaggio normalizzato
                    travel_time_norm = route.travel_times_min[i] / 180.0 if i < len(route.travel_times_min) else 0.5
                    adjacency_matrix[stop1_idx, stop2_idx] = travel_time_norm
                    adjacency_matrix[stop2_idx, stop1_idx] = travel_time_norm  # Bidirezionale
        
        # Genera scenari di conflitto sintetici
        conflict_scenarios = self._generate_conflict_scenarios(num_scenarios=5000)
        
        # Salva dataset
        np.savez_compressed(
            output_file,
            route_features=route_features,
            adjacency_matrix=adjacency_matrix,
            conflict_scenarios=conflict_scenarios,
            country_stats=self.country_stats,
            num_routes=len(self.routes),
            num_stops=len(self.stops),
            metadata={'routes': route_metadata, 'stops': self.stops}
        )
        
        logger.info(f"✓ Dataset salvato: {output_file}")
        logger.info(f"   Shape route_features: {route_features.shape}")
        logger.info(f"   Shape adjacency_matrix: {adjacency_matrix.shape}")
        logger.info(f"   Conflict scenarios: {len(conflict_scenarios)}")
        
        return True
    
    def _time_to_minutes(self, time_str: str) -> float:
        """Converte HH:MM:SS in minuti dal midnight."""
        parts = time_str.split(':')
        hours = int(parts[0])
        minutes = int(parts[1])
        seconds = int(parts[2]) if len(parts) > 2 else 0
        return hours * 60 + minutes + seconds / 60.0
    
    def _estimate_avg_speed(self, trip_stops: pd.DataFrame, stops_df: pd.DataFrame) -> float:
        """Stima velocità media da coordinate e tempi."""
        if len(trip_stops) < 2:
            return 100.0  # Default
        
        total_distance_km = 0.0
        total_time_min = 0.0
        
        for i in range(len(trip_stops) - 1):
            stop1_id = trip_stops.iloc[i]['stop_id']
            stop2_id = trip_stops.iloc[i + 1]['stop_id']
            
            # Trova coordinate
            stop1 = stops_df[stops_df['stop_id'] == stop1_id]
            stop2 = stops_df[stops_df['stop_id'] == stop2_id]
            
            if len(stop1) > 0 and len(stop2) > 0:
                lat1, lon1 = stop1.iloc[0]['stop_lat'], stop1.iloc[0]['stop_lon']
                lat2, lon2 = stop2.iloc[0]['stop_lat'], stop2.iloc[0]['stop_lon']
                
                # Distanza haversine (approssimata)
                distance = self._haversine_distance(lat1, lon1, lat2, lon2)
                total_distance_km += distance
                
                # Tempo
                dep = trip_stops.iloc[i]['departure_time']
                arr = trip_stops.iloc[i + 1]['arrival_time']
                try:
                    time = self._time_to_minutes(arr) - self._time_to_minutes(dep)
                    if time < 0:
                        time += 24 * 60
                    total_time_min += time
                except:
                    pass
        
        if total_time_min > 0:
            avg_speed = (total_distance_km / total_time_min) * 60  # km/h
            return min(avg_speed, 350.0)  # Cap a 350 km/h
        else:
            return 100.0
    
    def _haversine_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calcola distanza tra due coordinate (km)."""
        from math import radians, sin, cos, sqrt, atan2
        
        R = 6371  # Raggio terra in km
        
        lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
        c = 2 * atan2(sqrt(a), sqrt(1-a))
        
        return R * c
    
    def _generate_conflict_scenarios(self, num_scenarios: int = 5000) -> List[Dict]:
        """Genera scenari di conflitto sintetici per training."""
        scenarios = []
        
        for _ in range(num_scenarios):
            # Scegli 2 rotte random
            if len(self.routes) < 2:
                break
            
            route1 = np.random.choice(self.routes)
            route2 = np.random.choice(self.routes)
            
            # Crea scenario conflitto
            scenario = {
                'route1_speed': route1.avg_speed_kmh,
                'route2_speed': route2.avg_speed_kmh,
                'route1_stops': len(route1.stops),
                'route2_stops': len(route2.stops),
                'same_country': float(route1.country == route2.country),
                'time_overlap': np.random.uniform(0.1, 0.9),  # Sovrapposizione temporale
                'track_conflict': np.random.choice([0, 1]),  # Stesso binario?
            }
            
            scenarios.append(scenario)
        
        return scenarios


def main():
    """Script principale."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Parsa GTFS europei per training')
    parser.add_argument('--input-dir', default='data/european',
                       help='Directory con file GTFS')
    parser.add_argument('--output', default='data/european_training_data.npz',
                       help='File output dataset')
    
    args = parser.parse_args()
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    # Parse e export
    parser = EuropeanGTFSParser(args.input_dir)
    success = parser.parse_all_available()
    
    if success > 0:
        parser.export_for_training(args.output)
        logger.info("\n✅ COMPLETATO! Dataset pronto per training.")
    else:
        logger.error("❌ Nessun dato disponibile per export.")


if __name__ == '__main__':
    main()
