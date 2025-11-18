"""
Script completo per acquisizione dati reali da fonti ferroviarie italiane.

Questo script:
1. Scarica il grafo dell'infrastruttura da OpenStreetMap
2. Scarica orari ufficiali in formato GTFS
3. Raccoglie dati real-time da viaggiatreno.it
4. Esporta tutto in formato pronto per training

Uso:
    python download_real_data.py --all
    python download_real_data.py --gtfs
    python download_real_data.py --graph
    python download_real_data.py --realtime
"""

import argparse
import sys
from pathlib import Path
import logging

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from data_acquisition.gtfs_parser import GTFSParser, download_gtfs_rfi
from data_acquisition.railway_graph import RailwayGraphBuilder, download_italy_railways
from data_acquisition.rfi_client import RFIDataClient, MAJOR_STATIONS

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def download_gtfs_data(output_dir: Path):
    """Scarica e processa dati GTFS."""
    logger.info("=" * 60)
    logger.info("FASE 1: Download dati GTFS (orari ufficiali)")
    logger.info("=" * 60)
    
    gtfs_path = output_dir / "gtfs_rfi.zip"
    
    # Scarica GTFS
    if not gtfs_path.exists():
        logger.info("\nScaricamento GTFS da RFI...")
        downloaded = download_gtfs_rfi(str(gtfs_path))
        
        if not downloaded:
            logger.warning("⚠ Download automatico fallito")
            logger.info("\nSoluzioni:")
            logger.info("1. Scarica manualmente da: https://www.rfi.it/it/trasparenza/open-data.html")
            logger.info("2. Usa GTFS da TransitFeeds: https://transitfeeds.com/p/trenitalia/1028")
            logger.info("3. Contatta RFI per accesso dati")
            return False
    else:
        logger.info(f"✓ GTFS già scaricato: {gtfs_path}")
    
    # Parse GTFS
    logger.info("\nProcessamento GTFS...")
    parser = GTFSParser(str(gtfs_path))
    parser.load()
    
    # Export per training
    from datetime import datetime
    parser.export_for_training(
        output_path=str(output_dir / "gtfs_training_data.npz"),
        start_date=datetime.now(),
        num_days=30  # 30 giorni di orari
    )
    
    logger.info("✓ Dati GTFS processati e esportati")
    return True


def download_graph_data(output_dir: Path):
    """Scarica grafo infrastruttura."""
    logger.info("=" * 60)
    logger.info("FASE 2: Download grafo infrastruttura (OpenStreetMap)")
    logger.info("=" * 60)
    
    graph_path = output_dir / "railway_graph.npz"
    
    if not graph_path.exists():
        logger.info("\nScaricamento rete ferroviaria italiana...")
        logger.warning("⚠ ATTENZIONE: Può richiedere diversi minuti!")
        
        try:
            builder = download_italy_railways()
            logger.info("✓ Grafo infrastruttura scaricato")
            return True
        
        except Exception as e:
            logger.error(f"Errore download grafo: {e}")
            logger.info("\nSoluzioni:")
            logger.info("1. Verifica connessione internet")
            logger.info("2. Scarica estratto Italia da Geofabrik: https://download.geofabrik.de/europe/italy.html")
            logger.info("3. Usa regione più piccola (es. solo Lombardia)")
            return False
    else:
        logger.info(f"✓ Grafo già scaricato: {graph_path}")
        return True


def collect_realtime_data(output_dir: Path, duration_hours: int = 1):
    """Raccoglie dati real-time."""
    logger.info("=" * 60)
    logger.info("FASE 3: Raccolta dati real-time (viaggiatreno.it)")
    logger.info("=" * 60)
    
    logger.info(f"\nRaccolta dati per {duration_hours} ore...")
    logger.warning("⚠ Il processo continuerà in background")
    logger.warning("  Premi Ctrl+C per interrompere")
    
    client = RFIDataClient()
    
    # Monitora stazioni principali
    stations_to_monitor = ['S01700', 'S08409', 'S05042']  # Milano, Roma, Bologna
    
    try:
        client.collect_historical_data(
            station_codes=stations_to_monitor,
            output_path=str(output_dir / "realtime_data.json"),
            duration_hours=duration_hours
        )
        logger.info("✓ Dati real-time raccolti")
        return True
    
    except KeyboardInterrupt:
        logger.info("\n⚠ Raccolta interrotta dall'utente")
        return False


def generate_sample_demo_data(output_dir: Path):
    """Genera dati demo per test rapido."""
    logger.info("=" * 60)
    logger.info("MODALITÀ DEMO: Generazione dati di esempio")
    logger.info("=" * 60)
    
    logger.info("\nTest connessione API viaggiatreno...")
    
    client = RFIDataClient()
    
    # Test API
    logger.info("\n1. Test ricerca stazione:")
    stations = client.search_station("Milano")
    if stations:
        logger.info(f"  ✓ Trovate {len(stations)} stazioni")
        for s in stations[:3]:
            logger.info(f"    - {s['name']}")
    else:
        logger.warning("  ⚠ Nessuna stazione trovata")
    
    logger.info("\n2. Test partenze Milano Centrale:")
    departures = client.get_station_departures('S01700')
    if departures:
        logger.info(f"  ✓ Trovate {len(departures)} partenze")
        for dep in departures[:3]:
            logger.info(f"    - {dep['category']} {dep['train_number']}: "
                       f"ritardo {dep['delay_minutes']} min")
    else:
        logger.warning("  ⚠ Nessuna partenza trovata")
    
    logger.info("\n3. Test statistiche ritardi:")
    stats = client.get_delays_statistics('S01700')
    if 'error' not in stats:
        logger.info(f"  ✓ Puntuali: {stats['on_time_percentage']:.1f}%")
        logger.info(f"  ✓ Ritardo medio: {stats['average_delay']:.1f} min")
    
    logger.info("\n✓ Test API completati con successo!")


def main():
    parser = argparse.ArgumentParser(
        description="Scarica dati reali per Railway AI Scheduler"
    )
    
    parser.add_argument('--all', action='store_true',
                       help='Scarica tutti i dati (GTFS + grafo + realtime)')
    parser.add_argument('--gtfs', action='store_true',
                       help='Scarica solo dati GTFS (orari)')
    parser.add_argument('--graph', action='store_true',
                       help='Scarica solo grafo infrastruttura')
    parser.add_argument('--realtime', action='store_true',
                       help='Raccoglie dati real-time')
    parser.add_argument('--demo', action='store_true',
                       help='Modalità demo: testa API senza download')
    parser.add_argument('--duration', type=int, default=1,
                       help='Durata raccolta real-time (ore)')
    parser.add_argument('--output', type=str, default='data',
                       help='Directory output dati')
    
    args = parser.parse_args()
    
    # Setup output directory
    output_dir = Path(args.output)
    output_dir.mkdir(exist_ok=True)
    
    logger.info("\n" + "=" * 60)
    logger.info("RAILWAY AI SCHEDULER - Acquisizione Dati Reali")
    logger.info("=" * 60)
    
    # Modalità demo
    if args.demo:
        generate_sample_demo_data(output_dir)
        return
    
    # Modalità normale
    success = True
    
    if args.all or args.gtfs:
        success &= download_gtfs_data(output_dir)
    
    if args.all or args.graph:
        success &= download_graph_data(output_dir)
    
    if args.all or args.realtime:
        success &= collect_realtime_data(output_dir, args.duration)
    
    # Se nessuna opzione specificata, mostra help
    if not any([args.all, args.gtfs, args.graph, args.realtime, args.demo]):
        parser.print_help()
        print("\n💡 Suggerimento: Inizia con --demo per testare le API")
        return
    
    # Summary
    logger.info("\n" + "=" * 60)
    if success:
        logger.info("✅ DOWNLOAD COMPLETATO CON SUCCESSO!")
        logger.info("=" * 60)
        logger.info(f"\nDati salvati in: {output_dir.absolute()}")
        logger.info("\nProssimi passi:")
        logger.info("  1. Verifica i dati scaricati")
        logger.info("  2. Integra con il generatore di dati sintetici")
        logger.info("  3. Addestra il modello con dati reali")
    else:
        logger.warning("⚠ DOWNLOAD COMPLETATO CON ERRORI")
        logger.info("=" * 60)
        logger.info("\nVerifica i log sopra per dettagli")


if __name__ == "__main__":
    main()
