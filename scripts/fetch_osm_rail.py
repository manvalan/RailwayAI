import requests
import json
import argparse
import logging
import math
import random
import os
import sys
from collections import deque

# Force INFO level logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def haversine(lat1, lon1, lat2, lon2):
    """Calculates distance between two lat/lon points in km."""
    R = 6371 # Earth radius in km
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return R * c

OVERPASS_MIRRORS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.nchc.org.tw/api/interpreter",
    "https://lz4.overpass-api.de/api/interpreter"
]

def fetch_railway_data(area_name: str):
    """
    Queries Overpass API with retry and mirror rotation.
    """
    logger.info(f"Fetching railway data for: {area_name}")
    
    # Query optimized: we only need nodes/ways with railway tags
    query = f"""
    [out:json][timeout:180];
    area[name="{area_name}"]->.searchArea;
    (
      way["railway"="rail"](area.searchArea);
      node["railway"~"station|halt|stop_position"](area.searchArea);
    );
    out body;
    >;
    out skel qt;
    """
    
    last_err = None
    for url in OVERPASS_MIRRORS:
        try:
            logger.info(f"Connecting to mirror: {url}")
            response = requests.post(url, data={'data': query}, timeout=190)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.warning(f"Mirror {url} failed: {e}")
            last_err = e
            continue
            
    logger.error(f"All Overpass mirrors failed. Last error: {last_err}")
    return None

def process_to_scenario(osm_data: dict, out_file: str):
    """
    Advanced Scenario Conversion:
    1. Builds a global graph of all rail nodes.
    2. Identifies stations and stop positions.
    3. Snaps stations to the nearest rail node if they are not naturally connected.
    4. Finds paths between stations.
    """
    elements = osm_data.get('elements', [])
    nodes_data = {n['id']: n for n in elements if n['type'] == 'node'}
    ways = [w for w in elements if w['type'] == 'way']
    
    # 1. Identify Station Nodes
    stations = []
    station_osm_to_id = {}
    
    for node_id, node in nodes_data.items():
        if 'tags' in node and node['tags'].get('railway') in ['station', 'halt', 'stop_position']:
            name = node['tags'].get('name')
            if not name: continue # skip unnamed stops
            
            s_id = len(stations)
            stations.append({
                "id": s_id,
                "name": name,
                "num_platforms": int(node['tags'].get('platforms', 2)),
                "lat": node['lat'],
                "lon": node['lon'],
                "osm_id": node_id
            })
            station_osm_to_id[node_id] = s_id

    if not stations:
        logger.error("No named stations or stops found!")
        return

    # 2. Build Adjacency List for all rail nodes
    adj = {}
    all_rail_nodes = set()
    for way in ways:
        w_nodes = way.get('nodes', [])
        if len(w_nodes) < 2: continue
        
        tags = way.get('tags', {})
        # Filter for heavy rail primarily, exclude light rail/tram unless critical
        if tags.get('railway') != 'rail': continue
        if tags.get('service') in ['yard', 'spur']: continue # exclude sidings
        
        for i in range(len(w_nodes) - 1):
            n1, n2 = w_nodes[i], w_nodes[i+1]
            if n1 not in adj: adj[n1] = []
            if n2 not in adj: adj[n2] = []
            
            node1_data = nodes_data.get(n1)
            node2_data = nodes_data.get(n2)
            if node1_data and node2_data:
                d = haversine(node1_data['lat'], node1_data['lon'], node2_data['lat'], node2_data['lon'])
                adj[n1].append((n2, d, tags))
                adj[n2].append((n1, d, tags))
                all_rail_nodes.add(n1)
                all_rail_nodes.add(n2)

    # 3. STATION SNAPPING: Ensure stations are part of the graph
    for s in stations:
        if s['osm_id'] not in adj:
            # Look for the nearest rail node within 500m
            min_d = 0.5 
            best_node = None
            for rail_node in all_rail_nodes:
                nd = nodes_data.get(rail_node)
                dist = haversine(s['lat'], s['lon'], nd['lat'], nd['lon'])
                if dist < min_d:
                    min_d = dist
                    best_node = rail_node
            
            if best_node:
                # Create a virtual edge to connect station to network
                adj[s['osm_id']] = [(best_node, min_d, {})]
                if best_node not in adj: adj[best_node] = []
                adj[best_node].append((s['osm_id'], min_d, {}))
                logger.info(f"Connected station '{s['name']}' to railway graph via snap (dist: {min_d:.3f}km)")

    # 4. Traverse the graph to connect stations
    tracks = []
    visited_station_pairs = set()

    for start_station in stations:
        start_osm = start_station['osm_id']
        if start_osm not in adj: continue
        
        # BFS to find reachable stations
        queue = deque([(start_osm, 0, {}, {start_osm})])
        while queue:
            curr_osm, dist, tags, path_visited = queue.popleft()
            
            # If current node is a station and not the source
            if curr_osm in station_osm_to_id and curr_osm != start_osm:
                target_id = station_osm_to_id[curr_osm]
                
                # Check if it's actually a different station (sometimes multiple OSM nodes have same name)
                if stations[target_id]['name'] == start_station['name']:
                    # Continue searching PAST this node if it's the same station complex
                    pass 
                else:
                    pair = tuple(sorted((start_station['id'], target_id)))
                    if pair not in visited_station_pairs:
                        visited_station_pairs.add(pair)
                        tracks.append({
                            "id": len(tracks),
                            "length_km": round(dist, 2),
                            "capacity": int(tags.get('tracks', 1)),
                            "is_single_track": tags.get('railway:traffic_mode') == 'single' or int(tags.get('tracks', '1')) == 1,
                            "station_ids": [start_station['id'], target_id]
                        })
                    continue # Stop at first real foreign station found in this direction

            if dist > 35: continue # Max segment length
            
            if curr_osm in adj:
                for neighbor, d, w_tags in adj[curr_osm]:
                    if neighbor not in path_visited:
                        queue.append((neighbor, dist + d, w_tags if w_tags else tags, path_visited | {neighbor}))

    # 5. Result
    scenario = {
        "stations": stations,
        "tracks": tracks,
        "trains": [] # trains are added by the idle trainer or manually
    }

    with open(out_file, 'w') as f:
        json.dump(scenario, f, indent=2)
    
    logger.info(f"Successfully processed scenario for area with {len(stations)} stations and {len(tracks)} tracks.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--area", type=str, default="Roma", help="OSM Area name")
    parser.add_argument("--output", type=str, default="scenarios/roma_network.json")
    
    args = parser.parse_args()
    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    
    data = fetch_railway_data(args.area)
    if data and data.get('elements'):
        process_to_scenario(data, args.output)
    else:
        logger.error(f"Failed to fetch data or no elements found for area: {args.area}")
        sys.exit(1)
