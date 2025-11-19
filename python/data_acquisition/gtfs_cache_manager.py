"""
GTFS Cache Manager - Gestione intelligente file GTFS con compressione.

Risolve il problema dei file GTFS troppo grandi per Git:
1. Download on-demand con caching locale
2. Estrazione solo dati essenziali (stops, routes, trips, stop_times)
3. Compressione efficiente con pickle + gzip
4. Metadata tracking per invalidazione cache

File GTFS raw (ZIP, centinaia di MB) → Cache compresso (pochi MB) → Git-friendly
"""

import logging
import pickle
import gzip
import hashlib
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import zipfile
import pandas as pd

logger = logging.getLogger(__name__)


class GTFSCache:
    """
    Gestione cache intelligente per dati GTFS.
    
    Vantaggi:
    - File originali ZIP (258MB) → Cache compresso (5-10MB)
    - Solo dati essenziali estratti
    - Invalidazione automatica se fonte cambia
    - Git-friendly (file piccoli)
    """
    
    def __init__(self, cache_dir: str = "data/gtfs_cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.metadata_file = self.cache_dir / "cache_metadata.json"
        self.metadata = self._load_metadata()
        
    def _load_metadata(self) -> Dict:
        """Carica metadata cache esistente."""
        if self.metadata_file.exists():
            with open(self.metadata_file, 'r') as f:
                return json.load(f)
        return {}
    
    def _save_metadata(self):
        """Salva metadata cache."""
        with open(self.metadata_file, 'w') as f:
            json.dump(self.metadata, f, indent=2)
    
    def _get_cache_key(self, country_code: str) -> str:
        """Genera chiave cache per paese."""
        return f"{country_code}_essential"
    
    def _get_cache_path(self, country_code: str) -> Path:
        """Path file cache compresso."""
        return self.cache_dir / f"{country_code}_essential.pkl.gz"
    
    def get_file_hash(self, file_path: Path) -> str:
        """Calcola hash SHA256 di un file."""
        sha256 = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                sha256.update(chunk)
        return sha256.hexdigest()
    
    def extract_essential_data(self, gtfs_zip_path: Path) -> Dict:
        """
        Estrae SOLO i dati essenziali dal GTFS.
        
        Invece di tenere tutto il GTFS (stop_times.txt può essere 100MB+),
        estrae solo le informazioni necessarie per training.
        
        Args:
            gtfs_zip_path: Path al file GTFS.zip
            
        Returns:
            Dict con dati essenziali compressi
        """
        logger.info(f"📦 Estrazione dati essenziali da {gtfs_zip_path.name}...")
        
        essential_data = {
            'country': gtfs_zip_path.stem.replace('_gtfs', ''),
            'extracted_at': datetime.now().isoformat(),
            'source_file_size_mb': gtfs_zip_path.stat().st_size / (1024 * 1024)
        }
        
        try:
            with zipfile.ZipFile(gtfs_zip_path, 'r') as zf:
                # 1. STOPS - Solo ID, nome, coordinate
                if 'stops.txt' in zf.namelist():
                    stops_df = pd.read_csv(zf.open('stops.txt'))
                    essential_data['stops'] = {
                        'stop_ids': stops_df['stop_id'].tolist(),
                        'stop_names': stops_df['stop_name'].tolist(),
                        'stop_lats': stops_df.get('stop_lat', []).tolist(),
                        'stop_lons': stops_df.get('stop_lon', []).tolist(),
                        'count': len(stops_df)
                    }
                    logger.info(f"  ✓ Stops: {len(stops_df)} fermate")
                
                # 2. ROUTES - Solo ID, nome, tipo
                if 'routes.txt' in zf.namelist():
                    routes_df = pd.read_csv(zf.open('routes.txt'))
                    # Filtra solo treni (route_type 2 o 100-199)
                    train_routes = routes_df[
                        (routes_df['route_type'] == 2) | 
                        ((routes_df['route_type'] >= 100) & (routes_df['route_type'] < 200))
                    ]
                    essential_data['routes'] = {
                        'route_ids': train_routes['route_id'].tolist(),
                        'route_names': train_routes.get('route_long_name', 
                                                       train_routes.get('route_short_name', [])).tolist(),
                        'route_types': train_routes['route_type'].tolist(),
                        'count': len(train_routes)
                    }
                    logger.info(f"  ✓ Routes: {len(train_routes)} rotte treni (filtrate da {len(routes_df)} totali)")
                
                # 3. TRIPS - Solo ID e route association (campione)
                if 'trips.txt' in zf.namelist():
                    trips_df = pd.read_csv(zf.open('trips.txt'))
                    # Filtra solo trips di rotte treni
                    if 'routes' in essential_data:
                        train_trip_ids = trips_df[
                            trips_df['route_id'].isin(essential_data['routes']['route_ids'])
                        ]
                        # Campiona max 1000 trips per performance
                        if len(train_trip_ids) > 1000:
                            train_trip_ids = train_trip_ids.sample(1000)
                        
                        essential_data['trips'] = {
                            'trip_ids': train_trip_ids['trip_id'].tolist(),
                            'route_ids': train_trip_ids['route_id'].tolist(),
                            'count': len(train_trip_ids)
                        }
                        logger.info(f"  ✓ Trips: {len(train_trip_ids)} corse (campionate)")
                
                # 4. STOP_TIMES - Solo per trips campionati, aggregati
                if 'stop_times.txt' in zf.namelist() and 'trips' in essential_data:
                    # NOTA: stop_times.txt può essere ENORME (100MB+)
                    # Leggiamo solo le righe necessarie
                    stop_times_chunks = []
                    trip_ids_set = set(essential_data['trips']['trip_ids'])
                    
                    # Leggi in chunks per gestire file grandi
                    for chunk in pd.read_csv(zf.open('stop_times.txt'), chunksize=10000):
                        filtered = chunk[chunk['trip_id'].isin(trip_ids_set)]
                        if len(filtered) > 0:
                            stop_times_chunks.append(filtered)
                    
                    if stop_times_chunks:
                        stop_times_df = pd.concat(stop_times_chunks, ignore_index=True)
                        
                        # Aggregazione per trip: sequenza fermate + tempi
                        trips_summary = []
                        for trip_id in essential_data['trips']['trip_ids'][:100]:  # Max 100 per cache size
                            trip_stops = stop_times_df[
                                stop_times_df['trip_id'] == trip_id
                            ].sort_values('stop_sequence')
                            
                            if len(trip_stops) > 0:
                                trips_summary.append({
                                    'trip_id': trip_id,
                                    'stop_sequence': trip_stops['stop_id'].tolist(),
                                    'departure_times': trip_stops['departure_time'].tolist(),
                                    'num_stops': len(trip_stops)
                                })
                        
                        essential_data['trip_patterns'] = trips_summary
                        logger.info(f"  ✓ Stop Times: {len(trips_summary)} pattern analizzati")
                
                # 5. Statistiche aggregate
                essential_data['statistics'] = self._compute_statistics(essential_data)
                
        except Exception as e:
            logger.error(f"Errore estrazione: {e}")
            raise
        
        return essential_data
    
    def _compute_statistics(self, data: Dict) -> Dict:
        """Calcola statistiche aggregate sui dati."""
        stats = {}
        
        if 'stops' in data:
            stats['total_stops'] = data['stops']['count']
        
        if 'routes' in data:
            stats['total_train_routes'] = data['routes']['count']
        
        if 'trips' in data:
            stats['sampled_trips'] = data['trips']['count']
        
        if 'trip_patterns' in data:
            avg_stops = sum(p['num_stops'] for p in data['trip_patterns']) / len(data['trip_patterns'])
            stats['avg_stops_per_trip'] = round(avg_stops, 1)
        
        return stats
    
    def compress_and_cache(self, country_code: str, gtfs_zip_path: Path) -> Path:
        """
        Estrae dati essenziali e crea cache compresso.
        
        Args:
            country_code: Codice paese (es. 'france_sncf')
            gtfs_zip_path: Path al file GTFS.zip originale
            
        Returns:
            Path al file cache compresso creato
        """
        cache_path = self._get_cache_path(country_code)
        
        logger.info(f"\n🔧 Creazione cache compresso per {country_code}...")
        logger.info(f"   File originale: {gtfs_zip_path.stat().st_size / (1024*1024):.1f} MB")
        
        # Estrai dati essenziali
        essential_data = self.extract_essential_data(gtfs_zip_path)
        
        # Comprimi con pickle + gzip (molto efficiente)
        with gzip.open(cache_path, 'wb', compresslevel=9) as f:
            pickle.dump(essential_data, f)
        
        cache_size_mb = cache_path.stat().st_size / (1024 * 1024)
        compression_ratio = gtfs_zip_path.stat().st_size / cache_path.stat().st_size
        
        logger.info(f"   Cache creato: {cache_size_mb:.1f} MB")
        logger.info(f"   Compressione: {compression_ratio:.1f}x più piccolo")
        logger.info(f"   ✅ Salvato: {cache_path}")
        
        # Aggiorna metadata
        cache_key = self._get_cache_key(country_code)
        self.metadata[cache_key] = {
            'country_code': country_code,
            'original_file': str(gtfs_zip_path),
            'original_size_mb': essential_data['source_file_size_mb'],
            'cache_size_mb': cache_size_mb,
            'compression_ratio': round(compression_ratio, 2),
            'created_at': datetime.now().isoformat(),
            'file_hash': self.get_file_hash(gtfs_zip_path),
            'statistics': essential_data.get('statistics', {})
        }
        self._save_metadata()
        
        return cache_path
    
    def load_from_cache(self, country_code: str) -> Optional[Dict]:
        """
        Carica dati da cache compresso.
        
        Args:
            country_code: Codice paese
            
        Returns:
            Dict con dati, None se cache non esiste
        """
        cache_path = self._get_cache_path(country_code)
        
        if not cache_path.exists():
            logger.warning(f"Cache non trovato per {country_code}")
            return None
        
        logger.info(f"📂 Caricamento da cache: {country_code}")
        
        try:
            with gzip.open(cache_path, 'rb') as f:
                data = pickle.load(f)
            
            logger.info(f"   ✓ Caricato: {len(data.get('stops', {}).get('stop_ids', []))} stops, "
                       f"{len(data.get('routes', {}).get('route_ids', []))} routes")
            return data
        
        except Exception as e:
            logger.error(f"Errore caricamento cache: {e}")
            return None
    
    def is_cache_valid(self, country_code: str, gtfs_zip_path: Path, 
                       max_age_days: int = 7) -> bool:
        """
        Verifica se cache è ancora valido.
        
        Args:
            country_code: Codice paese
            gtfs_zip_path: Path file GTFS originale
            max_age_days: Età massima cache in giorni
            
        Returns:
            True se cache valido
        """
        cache_key = self._get_cache_key(country_code)
        
        if cache_key not in self.metadata:
            return False
        
        cache_info = self.metadata[cache_key]
        
        # Check 1: File cache esiste?
        cache_path = self._get_cache_path(country_code)
        if not cache_path.exists():
            return False
        
        # Check 2: File originale cambiato?
        if gtfs_zip_path.exists():
            current_hash = self.get_file_hash(gtfs_zip_path)
            if current_hash != cache_info.get('file_hash'):
                logger.info(f"⚠️  File GTFS cambiato per {country_code}, cache invalidato")
                return False
        
        # Check 3: Cache troppo vecchio?
        created_at = datetime.fromisoformat(cache_info['created_at'])
        age_days = (datetime.now() - created_at).days
        if age_days > max_age_days:
            logger.info(f"⚠️  Cache {country_code} ha {age_days} giorni (max {max_age_days})")
            return False
        
        return True
    
    def get_or_create_cache(self, country_code: str, gtfs_zip_path: Path) -> Dict:
        """
        Ottiene cache esistente o lo crea se necessario.
        
        Args:
            country_code: Codice paese
            gtfs_zip_path: Path file GTFS
            
        Returns:
            Dict con dati essenziali
        """
        # Prova a caricare cache esistente
        if self.is_cache_valid(country_code, gtfs_zip_path):
            data = self.load_from_cache(country_code)
            if data:
                logger.info(f"✓ Usando cache esistente per {country_code}")
                return data
        
        # Cache non valido o non esiste, crealo
        logger.info(f"🔨 Cache non valido o assente, creazione nuovo cache...")
        self.compress_and_cache(country_code, gtfs_zip_path)
        
        return self.load_from_cache(country_code)
    
    def list_cached_countries(self) -> List[str]:
        """Lista paesi con cache disponibile."""
        cached = []
        for cache_file in self.cache_dir.glob("*_essential.pkl.gz"):
            country_code = cache_file.stem.replace('_essential', '')
            cached.append(country_code)
        return cached
    
    def get_cache_stats(self) -> Dict:
        """Statistiche globali cache."""
        total_size_mb = sum(
            f.stat().st_size / (1024*1024) 
            for f in self.cache_dir.glob("*.pkl.gz")
        )
        
        return {
            'cached_countries': len(self.list_cached_countries()),
            'total_cache_size_mb': round(total_size_mb, 2),
            'cache_directory': str(self.cache_dir),
            'metadata_entries': len(self.metadata)
        }


def main():
    """Test e utility CLI."""
    import argparse
    
    parser = argparse.ArgumentParser(description='GTFS Cache Manager')
    parser.add_argument('--create', action='store_true',
                       help='Crea cache per tutti i GTFS disponibili')
    parser.add_argument('--list', action='store_true',
                       help='Lista cache esistenti')
    parser.add_argument('--stats', action='store_true',
                       help='Mostra statistiche cache')
    parser.add_argument('--country', type=str,
                       help='Codice paese specifico')
    
    args = parser.parse_args()
    
    logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')
    
    cache_manager = GTFSCache()
    
    if args.list or (not args.create and not args.stats):
        print("\n📦 CACHE GTFS DISPONIBILI:\n")
        cached = cache_manager.list_cached_countries()
        if cached:
            for country in cached:
                cache_key = cache_manager._get_cache_key(country)
                if cache_key in cache_manager.metadata:
                    info = cache_manager.metadata[cache_key]
                    print(f"  ✓ {country}")
                    print(f"    Size: {info['cache_size_mb']:.1f} MB "
                          f"(compresso {info['compression_ratio']:.1f}x)")
                    print(f"    Stops: {info['statistics'].get('total_stops', 0)}, "
                          f"Routes: {info['statistics'].get('total_train_routes', 0)}")
                    print()
        else:
            print("  Nessun cache disponibile.\n")
    
    if args.stats:
        print("\n📊 STATISTICHE CACHE:\n")
        stats = cache_manager.get_cache_stats()
        for key, value in stats.items():
            print(f"  {key}: {value}")
        print()
    
    if args.create:
        print("\n🔧 CREAZIONE CACHE PER TUTTI I GTFS...\n")
        
        gtfs_dir = Path("data/european")
        gtfs_files = list(gtfs_dir.glob("*_gtfs.zip"))
        
        if not gtfs_files:
            print("❌ Nessun file GTFS trovato in data/european/")
            return
        
        for gtfs_file in gtfs_files:
            country_code = gtfs_file.stem.replace('_gtfs', '')
            
            if args.country and country_code != args.country:
                continue
            
            print(f"\n{'='*60}")
            print(f"Processing: {country_code}")
            print('='*60)
            
            cache_manager.get_or_create_cache(country_code, gtfs_file)
        
        print(f"\n{'='*60}")
        print("✅ COMPLETATO!")
        print('='*60)
        stats = cache_manager.get_cache_stats()
        print(f"\nCache totale: {stats['total_cache_size_mb']:.1f} MB per {stats['cached_countries']} paesi")


if __name__ == '__main__':
    main()
