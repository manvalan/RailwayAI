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

COUNTRY_MAPPING = {
    "italia": "Italy", "lazio": "Lazio", "toscana": "Tuscany", "lombardia": "Lombardy",
    "roma": "Città metropolitana di Roma Capitale", "milano": "Milano", "firenze": "Firenze"
}

def fetch_railway_data(area_name: str):
    """
    Queries Overpass API with retry and mirror rotation.
    """
    normalized_area = COUNTRY_MAPPING.get(area_name.lower(), area_name)
    logger.info(f"Fetching railway data for: {normalized_area} (original: {area_name})")
    
    # Query optimized: we search for nodes, ways and relations for stations
    # but only ways for the tracks themselves.
    query = f"""
    [out:json][timeout:180];
    area[name="{normalized_area}"]->.searchArea;
    (
      way["railway"="rail"](area.searchArea);
      node["railway"~"station|halt|stop_position"](area.searchArea);
      way["railway"~"station|halt"](area.searchArea);
      relation["railway"~"station|halt"](area.searchArea);
    );
    out body;
    >;
    out skel qt;
    """
    
    last_err = None
    for url in OVERPASS_MIRRORS:
        try:
            logger.info(f"Connecting to mirror: {url} ...")
            response = requests.post(url, data={'data': query}, timeout=190)
            response.raise_for_status()
            resp_json = response.json()
            
            elements = resp_json.get('elements', [])
            ways_count = len([e for e in elements if e['type'] == 'way'])
            nodes_count = len([e for e in elements if e['type'] == 'node'])
            
            if elements and ways_count > 0:
                logger.info(f"Success! Found {len(elements)} elements ({ways_count} ways, {nodes_count} nodes).")
                return resp_json
            
            logger.warning(f"Mirror {url} returned insufficient data (ways: {ways_count}).")
        except Exception as e:
            logger.warning(f"Mirror {url} failed: {e}")
            last_err = e
            continue
            
    logger.error(f"All Overpass mirrors failed or returned no tracks. Potential area name mismatch: {normalized_area}")
    return None

def process_to_scenario(osm_data: dict, out_file: str):
    """
    Advanced Scenario Conversion:
    1. Builds a global graph of all rail nodes.
    2. Identifies stations (nodes, centroids of ways/relations).
    3. Snaps stations to the nearest rail node.
    4. Finds paths between stations.
    """
    elements = osm_data.get('elements', [])
    nodes_data = {n['id']: n for n in elements if n['type'] == 'node'}
    ways = [w for w in elements if w['type'] == 'way']
    # Relations are harder, but we can try to extract centroids if they have tags
    relations = [r for r in elements if r['type'] == 'relation']
    
    # 1. Identify Station Nodes
    stations = []
    station_osm_to_id = {}
    
    def add_station(osm_id, name, lat, lon, platforms=2):
        if not name: return
        s_id = len(stations)
        # Avoid duplicate stations by name in same location (within 200m)
        for existing in stations:
            if existing['name'] == name and haversine(lat, lon, existing['lat'], existing['lon']) < 0.2:
                station_osm_to_id[osm_id] = existing['id']
                return
        
        stations.append({
            "id": s_id,
            "name": name,
            "num_platforms": int(platforms),
            "lat": lat,
            "lon": lon,
            "osm_id": osm_id
        })
        station_osm_to_id[osm_id] = s_id

    # Process nodes for stations
    for node_id, node in nodes_data.items():
        tags = node.get('tags', {})
        if tags.get('railway') in ['station', 'halt', 'stop_position']:
            add_station(node_id, tags.get('name'), node['lat'], node['lon'], tags.get('platforms', 2))

    # Process ways as potential station centroids
    for way in ways:
        tags = way.get('tags', {})
        if tags.get('railway') in ['station', 'halt'] and tags.get('name'):
            # Calculate centroid
            w_nodes = way.get('nodes', [])
            lat_sum = 0
            lon_sum = 0
            count = 0
            for nid in w_nodes:
                nd = nodes_data.get(nid)
                if nd:
                    lat_sum += nd['lat']
                    lon_sum += nd['lon']
                    count += 1
            if count > 0:
                add_station(way['id'], tags.get('name'), lat_sum/count, lon_sum/count, tags.get('platforms', 2))

    if not stations:
        logger.error("No stations found in OSM data! Check if tags 'railway=station' or 'railway=stop_position' exist with a 'name'.")
        sys.exit(1)


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

    if not tracks:
        logger.error("No tracks or connections could be reconstructed between stations!")
        sys.exit(1)

    # 5. Result
    scenario = {
        "stations": stations,
        "tracks": tracks,
        "trains": [] # trains are added by the idle trainer or manually
    }

    with open(out_file, 'w') as f:
        json.dump(scenario, f, indent=2)
    
    logger.info(f"Successfully processed scenario with {len(stations)} stations and {len(tracks)} tracks.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--area", type=str, default="Roma", help="OSM Area name")
    parser.add_argument("--output", type=str, default="scenarios/roma_network.json")
    
    args = parser.parse_args()
    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    
    data = fetch_railway_data(args.area)
    if data:
        process_to_scenario(data, args.output)
    else:
        logger.error(f"Failed to fetch data for area: {args.area}")
        sys.exit(1)
