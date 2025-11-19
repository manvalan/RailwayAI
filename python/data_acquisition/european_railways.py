"""
Modulo per acquisizione dati da reti ferroviarie europee multiple.

Supporta:
- 🇫🇷 Francia: SNCF (TGV, Intercités, TER)
- 🇩🇪 Germania: Deutsche Bahn (ICE, IC, RE, S-Bahn)
- 🇨🇭 Svizzera: SBB/CFF/FFS
- 🇦🇹 Austria: ÖBB
- 🇪🇸 Spagna: Renfe (AVE, Alvia, Avant)
- 🇳🇱 Paesi Bassi: NS (Nederlandse Spoorwegen)

Fonti dati:
- GTFS feed pubblici (TransitFeeds, Mobility Database)
- OpenStreetMap (infrastruttura)
- API ufficiali quando disponibili
"""

import logging
import requests
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import zipfile
import io

logger = logging.getLogger(__name__)


# =============================================================================
# GTFS Feed URLs per paese - Mirror pubblici da Mobility Database
# =============================================================================

EUROPEAN_GTFS_FEEDS = {
    # Francia - SNCF
    'france_sncf': {
        'name': 'SNCF (Francia)',
        'url': 'https://transport.data.gouv.fr',
        'direct_download': 'https://eu.ftp.opendatasoft.com/sncf/gtfs/export-ter-gtfs-last.zip',
        'alternative_url': 'https://ressources.data.sncf.com/api/datasets/1.0/sncf-ter-gtfs/attachments/sncf_ter_gtfs_zip/',
        'coverage': 'Nazionale (TGV, Intercités, TER)',
        'update_frequency': 'Giornaliero',
        'notes': 'Include TGV alta velocità e treni regionali'
    },
    
    # Germania - Deutsche Bahn
    'germany_db': {
        'name': 'Deutsche Bahn (Germania)',
        'url': 'https://data.deutschebahn.com',
        'direct_download': 'https://download-data.deutschebahn.com/static/datasets/gtfs-germany/latest.zip',
        'alternative_url': 'https://gtfs.de/de/feeds/de_db/',
        'coverage': 'Nazionale (ICE, IC, RE, RB, S-Bahn)',
        'update_frequency': 'Settimanale',
        'notes': 'Rete più grande d\'Europa, include treni ad alta velocità ICE',
        'verify_ssl': False  # SSL cert issues temporanei
    },
    
    # Svizzera - SBB/CFF/FFS
    'switzerland_sbb': {
        'name': 'SBB/CFF/FFS (Svizzera)',
        'url': 'https://opentransportdata.swiss',
        'direct_download': 'https://opentransportdata.swiss/dataset/6f55f96d-7644-4901-b927-e9cf05a8c7f0/resource/c2c90c31-89e1-4b3c-8314-eaf84df675d1/download/gtfsfp20243.zip',
        'coverage': 'Nazionale (IC, RE, S-Bahn)',
        'update_frequency': 'Annuale con aggiornamenti',
        'notes': 'Rete molto puntuale e efficiente, ottimo per training'
    },
    
    # Austria - ÖBB
    'austria_oebb': {
        'name': 'ÖBB (Austria)',
        'url': 'https://www.oebb.at/de/rechtliches/open-data',
        'direct_download': 'https://data.oebb.at/sites/default/files/gtfs-at.zip',
        'alternative_url': 'https://transitfeeds.com/p/obb/608/latest/download',
        'coverage': 'Nazionale (Railjet, IC, RE)',
        'update_frequency': 'Giornaliero',
        'notes': 'Include collegamenti internazionali'
    },
    
    # Spagna - Renfe  
    'spain_renfe': {
        'name': 'Renfe (Spagna)',
        'url': 'https://data.renfe.com',
        'direct_download': 'https://transitfeeds.com/p/renfe/1016/latest/download',
        'coverage': 'AVE alta velocità + Alvia + Media Distancia',
        'update_frequency': 'Settimanale',
        'notes': 'Una delle reti AVE più estese al mondo'
    },
    
    # Paesi Bassi - NS
    'netherlands_ns': {
        'name': 'NS (Paesi Bassi)',
        'url': 'https://www.ns.nl/en/travel-information/ns-api',
        'direct_download': 'http://gtfs.ovapi.nl/nl/gtfs-nl.zip',
        'coverage': 'Nazionale (IC, Sprinter)',
        'update_frequency': 'Giornaliero',
        'notes': 'Rete molto densa, ottima per scenari urbani'
    },
    
    # Italia - RFI/Trenitalia (già implementato, incluso per completezza)
    'italy_rfi': {
        'name': 'RFI/Trenitalia (Italia)',
        'url': 'https://www.rfi.it/it/trasparenza/open-data.html',
        'direct_download': 'https://transitfeeds.com/p/trenitalia/1028/latest/download',
        'coverage': 'Nazionale (Frecciarossa, Intercity, Regionale)',
        'update_frequency': 'Settimanale',
        'notes': 'Include rete ad alta velocità Frecciarossa'
    }
}


# =============================================================================
# Caratteristiche reti per paese (per training)
# =============================================================================

NETWORK_CHARACTERISTICS = {
    'france_sncf': {
        'avg_speed_kmh': 220,  # TGV molto veloce
        'track_gauge_mm': 1435,  # Standard
        'electrification': 0.85,  # 85% elettrificata
        'single_track_ratio': 0.25,
        'punctuality_rate': 0.88,  # 88% puntualità
        'major_lines': ['Paris-Lyon (LGV)', 'Paris-Marseille', 'Paris-Bordeaux', 'Paris-Lille']
    },
    
    'germany_db': {
        'avg_speed_kmh': 180,  # ICE veloce
        'track_gauge_mm': 1435,
        'electrification': 0.90,  # 90% elettrificata
        'single_track_ratio': 0.30,
        'punctuality_rate': 0.75,  # 75% puntualità (in miglioramento)
        'major_lines': ['Hamburg-München', 'Berlin-Köln', 'Frankfurt-Basel', 'München-Berlin']
    },
    
    'switzerland_sbb': {
        'avg_speed_kmh': 150,
        'track_gauge_mm': 1435,
        'electrification': 1.00,  # 100% elettrificata!
        'single_track_ratio': 0.35,
        'punctuality_rate': 0.92,  # Migliore in Europa
        'major_lines': ['Genève-Zürich', 'Basel-Zürich-Chur', 'Zürich-Bern-Lausanne']
    },
    
    'austria_oebb': {
        'avg_speed_kmh': 170,
        'track_gauge_mm': 1435,
        'electrification': 0.88,
        'single_track_ratio': 0.40,
        'punctuality_rate': 0.85,
        'major_lines': ['Wien-Salzburg', 'Wien-Graz', 'Innsbruck-Salzburg']
    },
    
    'spain_renfe': {
        'avg_speed_kmh': 250,  # AVE molto veloce
        'track_gauge_mm': 1435,  # Standard gauge per AVE, 1668 per linee tradizionali
        'electrification': 0.80,
        'single_track_ratio': 0.20,
        'punctuality_rate': 0.90,
        'major_lines': ['Madrid-Barcelona', 'Madrid-Sevilla', 'Madrid-Valencia']
    },
    
    'netherlands_ns': {
        'avg_speed_kmh': 140,
        'track_gauge_mm': 1435,
        'electrification': 0.95,
        'single_track_ratio': 0.15,  # Molto basso, rete densa
        'punctuality_rate': 0.92,
        'major_lines': ['Amsterdam-Rotterdam', 'Amsterdam-Utrecht', 'Den Haag-Utrecht']
    },
    
    'italy_rfi': {
        'avg_speed_kmh': 200,  # Frecciarossa
        'track_gauge_mm': 1435,
        'electrification': 0.75,
        'single_track_ratio': 0.35,
        'punctuality_rate': 0.82,
        'major_lines': ['Milano-Roma', 'Roma-Napoli', 'Torino-Salerno', 'Milano-Venezia']
    }
}


class EuropeanRailwayDataCollector:
    """
    Raccoglitore dati da multiple reti ferroviarie europee.
    """
    
    def __init__(self, output_dir: str = "data/european"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.downloaded_feeds = {}
        
    def download_gtfs(self, country_code: str, force: bool = False) -> Optional[Path]:
        """
        Scarica GTFS feed per un paese specifico.
        
        Args:
            country_code: Codice paese (es. 'france_sncf', 'germany_db')
            force: Forza re-download anche se già presente
            
        Returns:
            Path al file GTFS scaricato, None se fallito
        """
        if country_code not in EUROPEAN_GTFS_FEEDS:
            logger.error(f"Paese non supportato: {country_code}")
            logger.info(f"Paesi disponibili: {list(EUROPEAN_GTFS_FEEDS.keys())}")
            return None
        
        feed_info = EUROPEAN_GTFS_FEEDS[country_code]
        output_path = self.output_dir / f"{country_code}_gtfs.zip"
        
        # Verifica se già scaricato
        if output_path.exists() and not force:
            logger.info(f"✓ {feed_info['name']} già scaricato: {output_path}")
            self.downloaded_feeds[country_code] = output_path
            return output_path
        
        logger.info(f"📥 Scaricamento {feed_info['name']}...")
        logger.info(f"   Coverage: {feed_info['coverage']}")
        logger.info(f"   URL: {feed_info['url']}")
        
        try:
            # Prova download diretto
            if 'direct_download' in feed_info and feed_info['direct_download']:
                verify_ssl = feed_info.get('verify_ssl', True)
                response = requests.get(
                    feed_info['direct_download'],
                    headers={'User-Agent': 'RailwayAI-Research/1.0'},
                    timeout=120,
                    verify=verify_ssl,
                    allow_redirects=True
                )
                
                if response.status_code == 200:
                    # Salva file
                    with open(output_path, 'wb') as f:
                        f.write(response.content)
                    
                    # Verifica che sia un ZIP valido
                    try:
                        with zipfile.ZipFile(output_path) as zf:
                            files = zf.namelist()
                            if 'stops.txt' in files and 'routes.txt' in files:
                                logger.info(f"✓ {feed_info['name']} scaricato con successo!")
                                logger.info(f"   File GTFS: {len(files)} files")
                                self.downloaded_feeds[country_code] = output_path
                                return output_path
                    except zipfile.BadZipFile:
                        logger.error("File ZIP non valido")
                        output_path.unlink()
                        return None
            
            # Fallback: istruzioni manuali
            logger.warning(f"⚠ Download automatico non disponibile per {feed_info['name']}")
            logger.info(f"\n📋 Download manuale:")
            logger.info(f"   1. Visita: {feed_info['url']}")
            logger.info(f"   2. Scarica il file GTFS")
            logger.info(f"   3. Salvalo come: {output_path}")
            logger.info(f"   Note: {feed_info['notes']}")
            
            return None
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Errore download: {e}")
            return None
    
    def download_all_countries(self, countries: Optional[List[str]] = None) -> Dict[str, Path]:
        """
        Scarica GTFS per tutti i paesi specificati (o tutti se None).
        
        Args:
            countries: Lista codici paesi, None = tutti
            
        Returns:
            Dizionario {country_code: path} dei download riusciti
        """
        if countries is None:
            countries = list(EUROPEAN_GTFS_FEEDS.keys())
        
        logger.info("=" * 70)
        logger.info(f"📥 DOWNLOAD DATI FERROVIARI EUROPEI - {len(countries)} paesi")
        logger.info("=" * 70)
        
        results = {}
        
        for i, country in enumerate(countries, 1):
            logger.info(f"\n[{i}/{len(countries)}] {country.upper()}")
            logger.info("-" * 70)
            
            path = self.download_gtfs(country)
            if path:
                results[country] = path
        
        # Riepilogo
        logger.info("\n" + "=" * 70)
        logger.info(f"✓ COMPLETATO: {len(results)}/{len(countries)} paesi scaricati")
        logger.info("=" * 70)
        
        for country, path in results.items():
            logger.info(f"  ✓ {EUROPEAN_GTFS_FEEDS[country]['name']}: {path.name}")
        
        if len(results) < len(countries):
            logger.info("\n⚠ Alcuni download non riusciti. Seguire istruzioni manuali sopra.")
        
        return results
    
    def get_network_stats(self) -> Dict:
        """Ottiene statistiche aggregate delle reti scaricate."""
        stats = {
            'total_countries': len(self.downloaded_feeds),
            'countries': list(self.downloaded_feeds.keys()),
            'characteristics': {}
        }
        
        for country in self.downloaded_feeds.keys():
            if country in NETWORK_CHARACTERISTICS:
                stats['characteristics'][country] = NETWORK_CHARACTERISTICS[country]
        
        return stats
    
    def export_unified_dataset(self, output_path: str = "data/european_unified.npz"):
        """
        Esporta dataset unificato da tutti i paesi scaricati.
        Include caratteristiche di rete per training multi-paese.
        """
        import numpy as np
        
        if not self.downloaded_feeds:
            logger.error("Nessun feed GTFS scaricato. Esegui download_all_countries() prima.")
            return False
        
        logger.info(f"\n📦 Creazione dataset unificato da {len(self.downloaded_feeds)} paesi...")
        
        # TODO: Implementare parsing e unificazione
        # Per ora crea struttura base
        
        unified_data = {
            'countries': list(self.downloaded_feeds.keys()),
            'network_characteristics': NETWORK_CHARACTERISTICS,
            'feed_paths': {k: str(v) for k, v in self.downloaded_feeds.items()},
            'timestamp': datetime.now().isoformat()
        }
        
        np.savez(output_path, **unified_data)
        logger.info(f"✓ Dataset unificato salvato: {output_path}")
        
        return True


def main():
    """Test script."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Scarica dati ferroviari europei')
    parser.add_argument('--countries', nargs='+', 
                       help='Paesi da scaricare (es: france_sncf germany_db)',
                       default=None)
    parser.add_argument('--all', action='store_true',
                       help='Scarica tutti i paesi disponibili')
    parser.add_argument('--list', action='store_true',
                       help='Mostra paesi disponibili')
    parser.add_argument('--output', default='data/european',
                       help='Directory output')
    
    args = parser.parse_args()
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    if args.list:
        print("\n🌍 RETI FERROVIARIE EUROPEE DISPONIBILI:\n")
        for code, info in EUROPEAN_GTFS_FEEDS.items():
            print(f"  {code:20} - {info['name']}")
            print(f"    Coverage: {info['coverage']}")
            print(f"    Update: {info['update_frequency']}")
            print(f"    {info['notes']}")
            print()
        return
    
    collector = EuropeanRailwayDataCollector(args.output)
    
    if args.all:
        countries = None
    elif args.countries:
        countries = args.countries
    else:
        # Default: paesi principali
        countries = ['france_sncf', 'germany_db', 'switzerland_sbb', 'austria_oebb']
    
    # Download
    results = collector.download_all_countries(countries)
    
    # Export unificato
    if results:
        collector.export_unified_dataset()
        
        # Mostra stats
        stats = collector.get_network_stats()
        print(f"\n📊 STATISTICHE DATASET:")
        print(f"   Paesi: {stats['total_countries']}")
        print(f"   Velocità media: {sum(c['avg_speed_kmh'] for c in stats['characteristics'].values()) / len(stats['characteristics']):.0f} km/h")
        print(f"   Puntualità media: {sum(c['punctuality_rate'] for c in stats['characteristics'].values()) / len(stats['characteristics']) * 100:.1f}%")


if __name__ == '__main__':
    main()
