"""
Client per API di dati ferroviari italiani.

Fonti dati disponibili:
1. Viaggiatreno API (RFI/Trenitalia) - dati real-time
2. RFI Open Data - infrastruttura e statistiche
3. ViaggiaTreno - ritardi e situazione treni

Note: Molte API non sono ufficialmente documentate.
"""

import requests
import json
from typing import Dict, List, Optional
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RFIDataClient:
    """
    Client per accedere a dati RFI/Trenitalia.
    
    API non ufficiali ma ampiamente utilizzate:
    - viaggiatreno.it - situazione treni in tempo reale
    - Trenitalia API interna
    """
    
    BASE_URL = "http://www.viaggiatreno.it/infomobilita/resteasy/viaggiatreno"
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Railway AI Scheduler)'
        })
    
    def search_station(self, station_name: str) -> List[Dict]:
        """
        Cerca stazione per nome.
        
        Args:
            station_name: Nome stazione (es. "Milano Centrale")
        
        Returns:
            Lista di stazioni trovate con id e nome completo
        """
        url = f"{self.BASE_URL}/cercaStazione/{station_name}"
        
        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            
            # Formato: "NOME|CODICE\nNOME2|CODICE2"
            results = []
            for line in response.text.strip().split('\n'):
                if '|' in line:
                    name, code = line.split('|')
                    results.append({
                        'name': name,
                        'code': code
                    })
            
            logger.info(f"Trovate {len(results)} stazioni per '{station_name}'")
            return results
        
        except Exception as e:
            logger.error(f"Errore ricerca stazione: {e}")
            return []
    
    def get_station_departures(self, station_code: str) -> List[Dict]:
        """
        Ottieni partenze da una stazione.
        
        Args:
            station_code: Codice stazione (es. "S01700" per Milano Centrale)
        
        Returns:
            Lista di treni in partenza con orari e ritardi
        """
        url = f"{self.BASE_URL}/partenze/{station_code}/{datetime.now().strftime('%a %b %d %Y %H:%M:%S GMT%z')}"
        
        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            departures = []
            for train in data:
                departure = {
                    'train_number': train.get('numeroTreno', ''),
                    'category': train.get('categoriaDescrizione', ''),
                    'destination': train.get('destinazione', ''),
                    'scheduled_time': train.get('orarioPartenza', ''),
                    'actual_time': train.get('orarioPartenzaReale', ''),
                    'delay_minutes': train.get('ritardo', 0),
                    'platform': train.get('binarioProgrammatoPartenzaDescrizione', ''),
                    'status': train.get('compRitardo', [])
                }
                departures.append(departure)
            
            logger.info(f"Partenze da stazione {station_code}: {len(departures)} treni")
            return departures
        
        except Exception as e:
            logger.error(f"Errore recupero partenze: {e}")
            return []
    
    def get_train_details(self, train_number: str, station_code: str) -> Optional[Dict]:
        """
        Ottieni dettagli completi di un treno.
        
        Args:
            train_number: Numero treno (es. "9624")
            station_code: Codice stazione di riferimento
        
        Returns:
            Dizionario con percorso completo e situazione
        """
        # Prima ottieni data partenza
        url = f"{self.BASE_URL}/cercaNumeroTrenoTrenoAutocomplete/{train_number}"
        
        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            
            # Formato: "NUMERO - ORIGINE|CODICE_STAZIONE-TIMESTAMP"
            parts = response.text.split('|')
            if len(parts) < 2:
                logger.warning(f"Treno {train_number} non trovato")
                return None
            
            station_timestamp = parts[1].split('-')
            origin_station = station_timestamp[0]
            
            # Ottieni andamento
            url2 = f"{self.BASE_URL}/andamentoTreno/{origin_station}/{train_number}/{datetime.now().strftime('%a %b %d %Y %H:%M:%S GMT%z')}"
            response2 = self.session.get(url2, timeout=10)
            response2.raise_for_status()
            
            data = response2.json()
            
            details = {
                'train_number': data.get('numeroTreno', ''),
                'category': data.get('categoria', ''),
                'origin': data.get('origine', ''),
                'destination': data.get('destinazione', ''),
                'departure_time': data.get('orarioPartenza', ''),
                'arrival_time': data.get('orarioArrivo', ''),
                'current_delay': data.get('ritardo', 0),
                'last_detection': data.get('stazioneUltimoRilevamento', ''),
                'stops': []
            }
            
            # Aggiungi fermate
            for stop in data.get('fermate', []):
                stop_info = {
                    'station': stop.get('stazione', ''),
                    'scheduled_arrival': stop.get('arrivo_teorico', ''),
                    'actual_arrival': stop.get('arrivo_reale', ''),
                    'scheduled_departure': stop.get('partenza_teorica', ''),
                    'actual_departure': stop.get('partenza_reale', ''),
                    'delay': stop.get('ritardo', 0),
                    'platform': stop.get('binarioProgrammatoArrivoDescrizione', '')
                }
                details['stops'].append(stop_info)
            
            logger.info(f"Dettagli treno {train_number}: {len(details['stops'])} fermate")
            return details
        
        except Exception as e:
            logger.error(f"Errore recupero dettagli treno: {e}")
            return None
    
    def get_delays_statistics(self, 
                             station_code: str,
                             hours_back: int = 24) -> Dict:
        """
        Calcola statistiche ritardi per una stazione.
        
        Args:
            station_code: Codice stazione
            hours_back: Ore di storico da analizzare
        
        Returns:
            Dizionario con statistiche
        """
        departures = self.get_station_departures(station_code)
        
        if not departures:
            return {'error': 'No data'}
        
        delays = [d['delay_minutes'] for d in departures if d['delay_minutes'] is not None]
        
        stats = {
            'total_trains': len(departures),
            'delayed_trains': sum(1 for d in delays if d > 5),
            'average_delay': sum(delays) / len(delays) if delays else 0,
            'max_delay': max(delays) if delays else 0,
            'on_time_percentage': sum(1 for d in delays if d <= 5) / len(delays) * 100 if delays else 0
        }
        
        logger.info(f"Statistiche ritardi: {stats['on_time_percentage']:.1f}% puntuali")
        return stats
    
    def collect_historical_data(self,
                               station_codes: List[str],
                               output_path: str,
                               duration_hours: int = 24):
        """
        Raccoglie dati storici per training.
        
        IMPORTANTE: Esegue polling ogni 5 minuti per durata specificata.
        Utile per creare dataset realistico di ritardi.
        
        Args:
            station_codes: Lista codici stazioni da monitorare
            output_path: Path file output JSON
            duration_hours: Durata raccolta dati
        """
        import time
        
        logger.info(f"Inizio raccolta dati storici ({duration_hours} ore)...")
        logger.warning("Questo processo richiederà molto tempo!")
        
        collected_data = []
        end_time = datetime.now().timestamp() + (duration_hours * 3600)
        
        try:
            while datetime.now().timestamp() < end_time:
                for station_code in station_codes:
                    departures = self.get_station_departures(station_code)
                    
                    for dep in departures:
                        record = {
                            'timestamp': datetime.now().isoformat(),
                            'station_code': station_code,
                            **dep
                        }
                        collected_data.append(record)
                
                # Salva incrementalmente
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(collected_data, f, indent=2, ensure_ascii=False)
                
                logger.info(f"Raccolti {len(collected_data)} record, prossimo aggiornamento in 5 min...")
                time.sleep(300)  # 5 minuti
        
        except KeyboardInterrupt:
            logger.info("Raccolta interrotta dall'utente")
        
        logger.info(f"✓ Dati salvati in: {output_path}")
        logger.info(f"  Totale record: {len(collected_data)}")


# Stazioni principali italiane (codici comuni)
MAJOR_STATIONS = {
    'Milano Centrale': 'S01700',
    'Roma Termini': 'S08409',
    'Firenze Santa Maria Novella': 'S06409',
    'Bologna Centrale': 'S05042',
    'Napoli Centrale': 'S09218',
    'Torino Porta Nuova': 'S00219',
    'Venezia Santa Lucia': 'S02593',
    'Genova Piazza Principe': 'S04216',
}


if __name__ == "__main__":
    # Esempio d'uso
    client = RFIDataClient()
    
    print("=== Test RFI Data Client ===\n")
    
    # 1. Cerca stazione
    print("1. Ricerca stazione 'Milano':")
    stations = client.search_station("Milano")
    for s in stations[:3]:
        print(f"  - {s['name']} (cod: {s['code']})")
    
    # 2. Partenze Milano Centrale
    print("\n2. Partenze da Milano Centrale:")
    departures = client.get_station_departures('S01700')
    for dep in departures[:5]:
        print(f"  - {dep['category']} {dep['train_number']} → {dep['destination']}")
        print(f"    Orario: {dep['scheduled_time']}, Ritardo: {dep['delay_minutes']} min")
    
    # 3. Statistiche ritardi
    print("\n3. Statistiche ritardi:")
    stats = client.get_delays_statistics('S01700')
    print(f"  Treni totali: {stats['total_trains']}")
    print(f"  Puntuali: {stats['on_time_percentage']:.1f}%")
    print(f"  Ritardo medio: {stats['average_delay']:.1f} min")
