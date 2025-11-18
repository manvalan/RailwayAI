"""
Costruttore del grafo dell'infrastruttura ferroviaria.
Usa dati da OpenStreetMap / OpenRailwayMap per ottenere la topologia reale.
"""

import requests
import json
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Set
from dataclasses import dataclass
import logging
import networkx as nx

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class RailwayNode:
    """Nodo del grafo (stazione o punto di intersezione)."""
    id: str
    name: Optional[str]
    lat: float
    lon: float
    node_type: str  # 'station', 'junction', 'switch'
    platforms: int = 0


@dataclass
class RailwayEdge:
    """Arco del grafo (binario tra due nodi)."""
    source: str
    target: str
    length_km: float
    track_count: int  # Numero di binari (1 = singolo, 2+ = doppio/multiplo)
    max_speed_kmh: float
    electrified: bool
    railway_type: str  # 'main', 'branch', 'siding', 'industrial'


class RailwayGraphBuilder:
    """
    Costruisce il grafo dell'infrastruttura ferroviaria da dati OSM.
    
    Fonti dati:
    - OpenStreetMap (OSM): https://www.openstreetmap.org/
    - OpenRailwayMap: https://www.openrailwaymap.org/
    - Overpass API: Query OSM per dati ferroviari
    """
    
    def __init__(self):
        self.graph = nx.MultiDiGraph()
        self.nodes: Dict[str, RailwayNode] = {}
        self.edges: List[RailwayEdge] = []
        
    def load_from_osm_region(self, 
                            bbox: Tuple[float, float, float, float],
                            country: str = "Italy"):
        """
        Scarica dati ferroviari da OSM per una regione specifica.
        
        Args:
            bbox: Bounding box (min_lat, min_lon, max_lat, max_lon)
            country: Nome paese per query
        """
        logger.info(f"Download dati OSM per regione: {bbox}")
        
        # Overpass API query per binari ferroviari
        overpass_url = "http://overpass-api.de/api/interpreter"
        
        # Query Overpass QL per ferrovie
        query = f"""
        [out:json][timeout:300];
        (
          // Stazioni ferroviarie
          node["railway"="station"]({bbox[0]},{bbox[1]},{bbox[2]},{bbox[3]});
          node["railway"="halt"]({bbox[0]},{bbox[1]},{bbox[2]},{bbox[3]});
          
          // Binari
          way["railway"="rail"]({bbox[0]},{bbox[1]},{bbox[2]},{bbox[3]});
          way["railway"="subway"]({bbox[0]},{bbox[1]},{bbox[2]},{bbox[3]});
          
          // Intersezioni
          node["railway"="junction"]({bbox[0]},{bbox[1]},{bbox[2]},{bbox[3]});
          node["railway"="switch"]({bbox[0]},{bbox[1]},{bbox[2]},{bbox[3]});
        );
        out body;
        >;
        out skel qt;
        """
        
        try:
            response = requests.post(
                overpass_url,
                data={'data': query},
                timeout=300
            )
            response.raise_for_status()
            osm_data = response.json()
            
            logger.info(f"✓ Ricevuti {len(osm_data.get('elements', []))} elementi OSM")
            
            # Processa dati
            self._process_osm_data(osm_data)
            
        except Exception as e:
            logger.error(f"Errore download OSM: {e}")
            logger.info("Suggerimenti:")
            logger.info("  1. Verifica connessione internet")
            logger.info("  2. Riduci dimensione bounding box")
            logger.info("  3. Scarica estratto OSM locale da Geofabrik")
    
    def load_from_osm_file(self, osm_file: str):
        """
        Carica dati da file OSM locale (formato .osm o .pbf).
        
        Args:
            osm_file: Path al file OSM
        """
        logger.info(f"Caricamento da file OSM: {osm_file}")
        
        # TODO: Implementare parser per file OSM/PBF
        # Richiede osmium o pyrosm
        logger.warning("Parser file OSM non ancora implementato")
        logger.info("Per ora usa load_from_osm_region() o scarica da Geofabrik")
    
    def _process_osm_data(self, osm_data: dict):
        """Processa dati OSM in formato JSON."""
        elements = osm_data.get('elements', [])
        
        # Prima pass: crea nodi
        node_coords = {}
        for elem in elements:
            if elem['type'] == 'node':
                node_id = f"osm_{elem['id']}"
                node_coords[node_id] = (elem['lat'], elem['lon'])
                
                tags = elem.get('tags', {})
                railway_tag = tags.get('railway', '')
                
                if railway_tag in ['station', 'halt', 'junction', 'switch']:
                    node = RailwayNode(
                        id=node_id,
                        name=tags.get('name', ''),
                        lat=elem['lat'],
                        lon=elem['lon'],
                        node_type=railway_tag,
                        platforms=int(tags.get('platforms', 0))
                    )
                    self.nodes[node_id] = node
                    self.graph.add_node(node_id, **node.__dict__)
        
        logger.info(f"  Nodi processati: {len(self.nodes)}")
        
        # Seconda pass: crea archi (binari)
        for elem in elements:
            if elem['type'] == 'way':
                tags = elem.get('tags', {})
                if tags.get('railway') not in ['rail', 'subway']:
                    continue
                
                nodes = elem.get('nodes', [])
                if len(nodes) < 2:
                    continue
                
                # Crea archi tra nodi consecutivi
                for i in range(len(nodes) - 1):
                    source = f"osm_{nodes[i]}"
                    target = f"osm_{nodes[i+1]}"
                    
                    # Calcola lunghezza approssimativa
                    if source in node_coords and target in node_coords:
                        length = self._haversine_distance(
                            node_coords[source],
                            node_coords[target]
                        )
                        
                        # Estrai metadati binario
                        track_count = int(tags.get('tracks', 1))
                        max_speed = float(tags.get('maxspeed', 100))
                        electrified = tags.get('electrified', 'no') != 'no'
                        railway_type = tags.get('usage', 'main')
                        
                        edge = RailwayEdge(
                            source=source,
                            target=target,
                            length_km=length,
                            track_count=track_count,
                            max_speed_kmh=max_speed,
                            electrified=electrified,
                            railway_type=railway_type
                        )
                        
                        self.edges.append(edge)
                        self.graph.add_edge(
                            source, target,
                            length=length,
                            tracks=track_count,
                            **edge.__dict__
                        )
        
        logger.info(f"  Archi (binari) processati: {len(self.edges)}")
    
    @staticmethod
    def _haversine_distance(coord1: Tuple[float, float], 
                           coord2: Tuple[float, float]) -> float:
        """
        Calcola distanza tra due coordinate GPS (in km).
        Formula di Haversine.
        """
        import math
        
        lat1, lon1 = math.radians(coord1[0]), math.radians(coord1[1])
        lat2, lon2 = math.radians(coord2[0]), math.radians(coord2[1])
        
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
        c = 2 * math.asin(math.sqrt(a))
        
        return 6371 * c  # Raggio terra in km
    
    def get_stations(self) -> List[RailwayNode]:
        """Ottieni tutte le stazioni."""
        return [n for n in self.nodes.values() if n.node_type in ['station', 'halt']]
    
    def get_tracks_between_stations(self, 
                                   station1_id: str, 
                                   station2_id: str) -> List[List[str]]:
        """
        Trova tutti i percorsi possibili tra due stazioni.
        
        Returns:
            Lista di path (ogni path è lista di node_id)
        """
        try:
            # Trova tutti i percorsi semplici (senza cicli)
            paths = list(nx.all_simple_paths(
                self.graph,
                station1_id,
                station2_id,
                cutoff=20  # Max 20 nodi intermedi
            ))
            return paths
        except nx.NetworkXNoPath:
            return []
    
    def is_single_track(self, source: str, target: str) -> bool:
        """Verifica se un binario è a binario unico."""
        edges = self.graph.get_edge_data(source, target)
        if not edges:
            return True
        
        # Controlla tutti gli archi paralleli
        return all(e.get('tracks', 1) == 1 for e in edges.values())
    
    def export_to_json(self, output_path: str):
        """Esporta grafo in formato JSON."""
        data = {
            'nodes': [node.__dict__ for node in self.nodes.values()],
            'edges': [edge.__dict__ for edge in self.edges],
            'metadata': {
                'num_stations': len(self.get_stations()),
                'num_tracks': len(self.edges),
                'total_length_km': sum(e.length_km for e in self.edges)
            }
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"✓ Grafo esportato in: {output_path}")
    
    def export_for_training(self, output_path: str):
        """
        Esporta in formato ottimizzato per training rete neurale.
        """
        import numpy as np
        
        # Converti nodi in array
        station_ids = []
        station_features = []
        
        for node in self.get_stations():
            station_ids.append(node.id)
            station_features.append([
                node.lat,
                node.lon,
                node.platforms,
                1.0 if node.node_type == 'station' else 0.0
            ])
        
        # Converti archi in matrice di adiacenza
        edge_features = []
        adjacency = []
        
        for edge in self.edges:
            try:
                src_idx = station_ids.index(edge.source)
                tgt_idx = station_ids.index(edge.target)
                
                adjacency.append([src_idx, tgt_idx])
                edge_features.append([
                    edge.length_km,
                    edge.track_count,
                    edge.max_speed_kmh,
                    1.0 if edge.electrified else 0.0,
                    1.0 if edge.track_count == 1 else 0.0  # is_single_track
                ])
            except ValueError:
                # Nodo non in lista stazioni
                continue
        
        # Salva
        np.savez_compressed(
            output_path,
            station_ids=np.array(station_ids),
            station_features=np.array(station_features, dtype=np.float32),
            adjacency=np.array(adjacency, dtype=np.int32),
            edge_features=np.array(edge_features, dtype=np.float32)
        )
        
        logger.info(f"✓ Grafo esportato per training: {output_path}")
        logger.info(f"  Stazioni: {len(station_ids)}")
        logger.info(f"  Collegamenti: {len(edge_features)}")


def download_italy_railways():
    """
    Scarica dati ferroviari dell'Italia.
    Usa bbox che copre l'intera Italia.
    """
    builder = RailwayGraphBuilder()
    
    # Bounding box Italia
    italy_bbox = (36.0, 6.5, 47.5, 19.0)  # (min_lat, min_lon, max_lat, max_lon)
    
    logger.info("Download rete ferroviaria italiana...")
    logger.warning("ATTENZIONE: Download può richiedere diversi minuti!")
    
    builder.load_from_osm_region(italy_bbox, country="Italy")
    
    # Export
    builder.export_to_json("data/italy_railway_graph.json")
    builder.export_for_training("data/italy_railway_graph.npz")
    
    # Statistiche
    stations = builder.get_stations()
    logger.info(f"\n✓ Rete italiana scaricata:")
    logger.info(f"  Stazioni: {len(stations)}")
    logger.info(f"  Binari: {len(builder.edges)}")
    
    single_track = sum(1 for e in builder.edges if e.track_count == 1)
    logger.info(f"  Binari singoli: {single_track} ({single_track/len(builder.edges)*100:.1f}%)")
    
    return builder


if __name__ == "__main__":
    # Esempio: scarica rete ferroviaria italiana
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == '--italy':
        download_italy_railways()
    else:
        print("Uso:")
        print("  python railway_graph.py --italy")
        print("\nScarica la rete ferroviaria italiana da OpenStreetMap")
