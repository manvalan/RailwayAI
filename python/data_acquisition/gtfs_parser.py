"""
Parser per dati GTFS (General Transit Feed Specification).
Formato standard per orari ferroviari utilizzato da RFI, Trenitalia, etc.

Documentazione GTFS: https://gtfs.org/
"""

import pandas as pd
import zipfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class Stop:
    """Rappresenta una fermata/stazione."""
    stop_id: str
    stop_name: str
    stop_lat: float
    stop_lon: float
    platform_code: Optional[str] = None
    parent_station: Optional[str] = None


@dataclass
class Route:
    """Rappresenta una linea ferroviaria."""
    route_id: str
    route_short_name: str
    route_long_name: str
    route_type: int  # 2 = rail
    agency_id: str


@dataclass
class Trip:
    """Rappresenta una corsa specifica di un treno."""
    trip_id: str
    route_id: str
    service_id: str
    trip_headsign: str
    direction_id: int
    shape_id: Optional[str] = None


@dataclass
class StopTime:
    """Orario di arrivo/partenza a una fermata."""
    trip_id: str
    arrival_time: str
    departure_time: str
    stop_id: str
    stop_sequence: int
    pickup_type: int = 0
    drop_off_type: int = 0


class GTFSParser:
    """
    Parser per file GTFS ferroviari.
    
    Scarica e processa dati da:
    - RFI (Rete Ferroviaria Italiana)
    - Trenitalia
    - Italo
    - Altri operatori europei
    """
    
    def __init__(self, gtfs_path: str):
        """
        Args:
            gtfs_path: Path al file .zip GTFS o alla directory estratta
        """
        self.gtfs_path = Path(gtfs_path)
        self.data_dir = None
        
        # DataFrames caricati
        self.stops_df: Optional[pd.DataFrame] = None
        self.routes_df: Optional[pd.DataFrame] = None
        self.trips_df: Optional[pd.DataFrame] = None
        self.stop_times_df: Optional[pd.DataFrame] = None
        self.calendar_df: Optional[pd.DataFrame] = None
        self.shapes_df: Optional[pd.DataFrame] = None
        
        logger.info(f"Inizializzato parser GTFS per: {gtfs_path}")
    
    def load(self):
        """Carica tutti i file GTFS necessari."""
        # Se è uno zip, estrailo
        if self.gtfs_path.suffix == '.zip':
            logger.info("Estrazione archivio GTFS...")
            with zipfile.ZipFile(self.gtfs_path, 'r') as zip_ref:
                extract_dir = self.gtfs_path.parent / self.gtfs_path.stem
                extract_dir.mkdir(exist_ok=True)
                zip_ref.extractall(extract_dir)
                self.data_dir = extract_dir
        else:
            self.data_dir = self.gtfs_path
        
        logger.info("Caricamento file GTFS...")
        
        # File obbligatori
        self.stops_df = self._load_csv('stops.txt')
        self.routes_df = self._load_csv('routes.txt')
        self.trips_df = self._load_csv('trips.txt')
        self.stop_times_df = self._load_csv('stop_times.txt')
        self.calendar_df = self._load_csv('calendar.txt')
        
        # File opzionali
        try:
            self.shapes_df = self._load_csv('shapes.txt')
        except FileNotFoundError:
            logger.warning("shapes.txt non trovato (opzionale)")
        
        logger.info("✓ File GTFS caricati con successo")
        self._log_statistics()
    
    def _load_csv(self, filename: str) -> pd.DataFrame:
        """Carica un file CSV GTFS."""
        filepath = self.data_dir / filename
        if not filepath.exists():
            raise FileNotFoundError(f"File GTFS mancante: {filename}")
        
        df = pd.read_csv(filepath, dtype=str)
        logger.info(f"  ✓ {filename}: {len(df)} righe")
        return df
    
    def _log_statistics(self):
        """Stampa statistiche sui dati caricati."""
        logger.info("\n=== Statistiche GTFS ===")
        logger.info(f"Fermate/Stazioni: {len(self.stops_df)}")
        logger.info(f"Linee: {len(self.routes_df)}")
        logger.info(f"Corse: {len(self.trips_df)}")
        logger.info(f"Orari fermata: {len(self.stop_times_df)}")
    
    def get_stations(self) -> List[Stop]:
        """
        Ottieni lista di tutte le stazioni (non piattaforme).
        
        Returns:
            Lista di oggetti Stop
        """
        # Filtra solo stazioni principali (location_type == 1 o parent_station è null)
        stations = self.stops_df[
            (self.stops_df.get('location_type', '0') == '1') |
            (self.stops_df['parent_station'].isna())
        ]
        
        result = []
        for _, row in stations.iterrows():
            stop = Stop(
                stop_id=row['stop_id'],
                stop_name=row['stop_name'],
                stop_lat=float(row['stop_lat']),
                stop_lon=float(row['stop_lon']),
                platform_code=row.get('platform_code'),
                parent_station=row.get('parent_station')
            )
            result.append(stop)
        
        logger.info(f"Trovate {len(result)} stazioni")
        return result
    
    def get_routes(self, route_type: int = 2) -> List[Route]:
        """
        Ottieni linee ferroviarie.
        
        Args:
            route_type: 2 = treni regionali, 100-199 = alta velocità
        
        Returns:
            Lista di Route
        """
        # Filtra per tipo (2 = rail)
        routes = self.routes_df[self.routes_df['route_type'] == str(route_type)]
        
        result = []
        for _, row in routes.iterrows():
            route = Route(
                route_id=row['route_id'],
                route_short_name=row.get('route_short_name', ''),
                route_long_name=row.get('route_long_name', ''),
                route_type=int(row['route_type']),
                agency_id=row.get('agency_id', '')
            )
            result.append(route)
        
        logger.info(f"Trovate {len(result)} linee ferroviarie")
        return result
    
    def get_trips_for_date(self, date: datetime) -> List[Trip]:
        """
        Ottieni tutte le corse attive in una specifica data.
        
        Args:
            date: Data per cui recuperare le corse
        
        Returns:
            Lista di Trip
        """
        # Determina service_id attivi per questa data
        weekday_col = [
            'monday', 'tuesday', 'wednesday', 'thursday',
            'friday', 'saturday', 'sunday'
        ][date.weekday()]
        
        active_services = self.calendar_df[
            (self.calendar_df['start_date'] <= date.strftime('%Y%m%d')) &
            (self.calendar_df['end_date'] >= date.strftime('%Y%m%d')) &
            (self.calendar_df[weekday_col] == '1')
        ]['service_id'].tolist()
        
        # Filtra trips per servizi attivi
        active_trips = self.trips_df[
            self.trips_df['service_id'].isin(active_services)
        ]
        
        result = []
        for _, row in active_trips.iterrows():
            trip = Trip(
                trip_id=row['trip_id'],
                route_id=row['route_id'],
                service_id=row['service_id'],
                trip_headsign=row.get('trip_headsign', ''),
                direction_id=int(row.get('direction_id', 0)),
                shape_id=row.get('shape_id')
            )
            result.append(trip)
        
        logger.info(f"Trovate {len(result)} corse per {date.strftime('%Y-%m-%d')}")
        return result
    
    def get_stop_times_for_trip(self, trip_id: str) -> List[StopTime]:
        """
        Ottieni tutti gli orari di fermata per una corsa.
        
        Args:
            trip_id: ID della corsa
        
        Returns:
            Lista di StopTime ordinati per sequenza
        """
        trip_stops = self.stop_times_df[
            self.stop_times_df['trip_id'] == trip_id
        ].sort_values('stop_sequence')
        
        result = []
        for _, row in trip_stops.iterrows():
            stop_time = StopTime(
                trip_id=row['trip_id'],
                arrival_time=row['arrival_time'],
                departure_time=row['departure_time'],
                stop_id=row['stop_id'],
                stop_sequence=int(row['stop_sequence']),
                pickup_type=int(row.get('pickup_type', 0)),
                drop_off_type=int(row.get('drop_off_type', 0))
            )
            result.append(stop_time)
        
        return result
    
    def build_schedule_matrix(self, date: datetime) -> pd.DataFrame:
        """
        Costruisce una matrice orari per training della rete neurale.
        
        Args:
            date: Data per cui generare la matrice
        
        Returns:
            DataFrame con colonne [trip_id, stop_id, arrival_time, departure_time, sequence]
        """
        trips = self.get_trips_for_date(date)
        trip_ids = [t.trip_id for t in trips]
        
        # Filtra stop_times per trips attivi
        schedule = self.stop_times_df[
            self.stop_times_df['trip_id'].isin(trip_ids)
        ].copy()
        
        # Converti tempi in minuti da mezzanotte
        schedule['arrival_minutes'] = schedule['arrival_time'].apply(self._time_to_minutes)
        schedule['departure_minutes'] = schedule['departure_time'].apply(self._time_to_minutes)
        
        # Merge con info stazioni
        schedule = schedule.merge(
            self.stops_df[['stop_id', 'stop_name', 'stop_lat', 'stop_lon']],
            on='stop_id',
            how='left'
        )
        
        # Merge con info routes
        schedule = schedule.merge(
            self.trips_df[['trip_id', 'route_id']],
            on='trip_id',
            how='left'
        )
        
        logger.info(f"Matrice orari: {len(schedule)} fermate programmate")
        return schedule
    
    @staticmethod
    def _time_to_minutes(time_str: str) -> int:
        """
        Converte orario GTFS in minuti da mezzanotte.
        
        GTFS permette ore > 24 (es. 25:30:00 = 01:30 del giorno dopo)
        """
        try:
            parts = time_str.split(':')
            hours = int(parts[0])
            minutes = int(parts[1])
            return hours * 60 + minutes
        except:
            return 0
    
    def export_for_training(self, 
                          output_path: str,
                          start_date: datetime,
                          num_days: int = 7):
        """
        Esporta dati in formato ottimizzato per training.
        
        Args:
            output_path: Path file output .npz
            start_date: Data inizio periodo
            num_days: Numero di giorni da esportare
        """
        logger.info(f"Esportazione dati per training ({num_days} giorni)...")
        
        all_schedules = []
        
        for day_offset in range(num_days):
            date = start_date + timedelta(days=day_offset)
            logger.info(f"  Processando {date.strftime('%Y-%m-%d')}...")
            
            schedule = self.build_schedule_matrix(date)
            schedule['date'] = date.strftime('%Y-%m-%d')
            all_schedules.append(schedule)
        
        # Concatena tutti i giorni
        full_schedule = pd.concat(all_schedules, ignore_index=True)
        
        # Salva in formato compresso
        import numpy as np
        
        np.savez_compressed(
            output_path,
            trip_ids=full_schedule['trip_id'].values,
            stop_ids=full_schedule['stop_id'].values,
            arrival_times=full_schedule['arrival_minutes'].values,
            departure_times=full_schedule['departure_minutes'].values,
            sequences=full_schedule['stop_sequence'].values,
            dates=full_schedule['date'].values
        )
        
        logger.info(f"✓ Dati esportati in: {output_path}")
        logger.info(f"  Totale fermate: {len(full_schedule)}")


def download_gtfs_rfi(output_path: str = "data/gtfs_rfi.zip"):
    """
    Scarica il feed GTFS ufficiale di RFI/Trenitalia.
    
    Note:
    - URL ufficiale RFI: https://www.rfi.it/it/trasparenza/open-data.html
    - Alcuni dati richiedono registrazione
    - Alternative: OpenStreetMap, viaggiatreno.it API
    """
    import requests
    
    # URL esempio (verificare sito RFI per URL aggiornato)
    gtfs_url = "https://transitfeeds.com/p/trenitalia/1028/latest/download"
    
    logger.info(f"Download GTFS da RFI...")
    logger.warning("NOTA: Verificare URL corretto sul sito RFI Open Data")
    
    try:
        response = requests.get(gtfs_url, stream=True)
        response.raise_for_status()
        
        with open(output_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        logger.info(f"✓ GTFS scaricato: {output_path}")
        return output_path
    
    except Exception as e:
        logger.error(f"Errore download GTFS: {e}")
        logger.info("Alternative:")
        logger.info("  1. Scarica manualmente da: https://www.rfi.it/")
        logger.info("  2. Usa OpenStreetMap data")
        logger.info("  3. Richiedi accesso API Trenitalia")
        return None


if __name__ == "__main__":
    # Esempio d'uso
    import sys
    
    if len(sys.argv) < 2:
        print("Uso: python gtfs_parser.py <path_to_gtfs.zip>")
        print("\nPer scaricare GTFS RFI:")
        print("  python gtfs_parser.py --download")
        sys.exit(1)
    
    if sys.argv[1] == '--download':
        gtfs_path = download_gtfs_rfi()
        if not gtfs_path:
            sys.exit(1)
    else:
        gtfs_path = sys.argv[1]
    
    # Parse GTFS
    parser = GTFSParser(gtfs_path)
    parser.load()
    
    # Statistiche
    stations = parser.get_stations()
    print(f"\nPrime 5 stazioni:")
    for station in stations[:5]:
        print(f"  - {station.stop_name} ({station.stop_id})")
    
    # Export per training
    today = datetime.now()
    parser.export_for_training(
        output_path="data/real_schedule_data.npz",
        start_date=today,
        num_days=7
    )
