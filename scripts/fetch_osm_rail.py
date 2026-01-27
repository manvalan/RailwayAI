import requests
import json
import argparse
import logging
import math

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def haversine(lat1, lon1, lat2, lon2):
    """Calculates distance between two lat/lon points in km."""
    R = 6371 # Earth radius in km
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return R * c

OVERPASS_URL = "http://overpass-api.de/api/interpreter"

def fetch_railway_data(area_name: str):
    """
    Queries Overpass API for railway infrastructure in a specific area.
    """
    logger.info(f"Fetching railway data for: {area_name}")
    
    query = f"""
    [out:json][timeout:90];
    area[name="{area_name}"]->.searchArea;
    (
      way["railway"="rail"](area.searchArea);
      node["railway"="station"](area.searchArea);
      node["railway"="halt"](area.searchArea);
    );
    out body;
    >;
    out skel qt;
    """
    
    response = requests.post(OVERPASS_URL, data={'data': query})
    if response.status_code != 200:
        logger.error(f"Error fetching data: {response.text}")
        return None
        
    return response.json()

def process_to_scenario(osm_data: dict, out_file: str):
    """
    Converts raw OSM JSON to RailwayAI Scenario format.
    """
    scenario = {
        "tracks": [],
        "stations": [],
        "trains": []
    }
    
    nodes = {n['id']: n for n in osm_data.get('elements', []) if n['type'] == 'node'}
    ways = [w for w in osm_data.get('elements', []) if w['type'] == 'way']
    
    # 1. Stations
    station_map = {} # OSM Node ID -> Scenario Station ID
    for node_id, node in nodes.items():
        if 'tags' in node and ('railway' in node['tags'] and node['tags']['railway'] in ['station', 'halt']):
            s_id = len(scenario['stations'])
            scenario['stations'].append({
                "id": s_id,
                "name": node['tags'].get('name', f"Station_{node_id}"),
                "num_platforms": int(node['tags'].get('platforms', 2))
            })
            station_map[node_id] = s_id
            
    # 2. Tracks (Ways)
    for way in ways:
        way_nodes = way.get('nodes', [])
        if len(way_nodes) < 2: continue
        
        # Find nearest stations to endpoints
        start_node = nodes.get(way_nodes[0])
        end_node = nodes.get(way_nodes[-1])
        
        if not start_node or not end_node: continue
        
        dist = haversine(start_node['lat'], start_node['lon'], end_node['lat'], end_node['lon'])
        
        track_id = len(scenario['tracks'])
        scenario['tracks'].append({
            "id": track_id,
            "length_km": round(dist, 2),
            "capacity": int(way.get('tags', {}).get('tracks', 1)),
            "is_single_track": way.get('tags', {}).get('railway:traffic_mode') == 'single',
            "station_ids": [0, 1] # Placeholder: would require KDTree for real mapping
        })
        
    # 3. Trains (Inject synthetic complex traffic)
    # Strategy: Place 1 train for every 5 tracks to create "Complexity"
    for i in range(len(scenario['tracks']) // 5):
        scenario['trains'].append({
            "id": i,
            "current_track": i * 5,
            "position_km": 0,
            "destination_station": random.choice(list(station_map.values())) if station_map else 0,
            "priority": random.randint(1, 10),
            "velocity_kmh": 140
        })

    with open(out_file, 'w') as f:
        json.dump(scenario, f, indent=2)
    logger.info(f"Scenario saved to {out_file} with {len(scenario['tracks'])} tracks.")

if __name__ == "__main__":
    import random
    parser = argparse.ArgumentParser()
    parser.add_argument("--area", type=str, default="Lombardia", help="OSM Area name (e.g. 'Italy', 'Berlin')")
    parser.add_argument("--output", type=str, default="europe_complex.json")
    
    args = parser.parse_args()
    
    data = fetch_railway_data(args.area)
    if data:
        process_to_scenario(data, args.output)
