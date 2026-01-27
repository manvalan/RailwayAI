import requests
import json
import argparse
import logging
import math
import random
import os

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
    [out:json][timeout:180];
    area[name="{area_name}"]->.searchArea;
    (
      way["railway"="rail"](area.searchArea);
      node["railway"~"station|halt"](area.searchArea);
    );
    out body;
    >;
    out skel qt;
    """
    
    try:
        response = requests.post(OVERPASS_URL, data={'data': query})
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"Error fetching data: {e}")
        return None

def process_to_scenario(osm_data: dict, out_file: str):
    """
    Converts raw OSM JSON to RailwayAI Scenario format with valid topology.
    """
    scenario = {
        "tracks": [],
        "stations": [],
        "trains": []
    }
    
    elements = osm_data.get('elements', [])
    nodes = {n['id']: n for n in elements if n['type'] == 'node'}
    ways = [w for w in elements if w['type'] == 'way']
    
    # 1. Identify Station Nodes
    station_nodes = []
    for node_id, node in nodes.items():
        if 'tags' in node and ('railway' in node['tags'] and node['tags']['railway'] in ['station', 'halt']):
            s_id = len(scenario['stations'])
            scenario['stations'].append({
                "id": s_id,
                "name": node['tags'].get('name', f"Station_{node_id}"),
                "num_platforms": int(node['tags'].get('platforms', 2)),
                "lat": node['lat'],
                "lon": node['lon'],
                "osm_id": node_id
            })
            station_nodes.append(node)
            
    if not scenario['stations']:
        logger.warning("No stations found. Creating dummy endpoints.")
        scenario['stations'].append({"id": 0, "name": "Source", "num_platforms": 2})
        scenario['stations'].append({"id": 1, "name": "Sink", "num_platforms": 2})

    # 2. Process Tracks (Ways)
    station_osm_ids = {s['osm_id']: s['id'] for s in scenario['stations'] if 'osm_id' in s}
    
    for way in ways:
        way_nodes = way.get('nodes', [])
        if len(way_nodes) < 2: continue
        
        start_node = nodes.get(way_nodes[0])
        end_node = nodes.get(way_nodes[-1])
        if not start_node or not end_node: continue
        
        # Calculate length
        length = 0
        for i in range(len(way_nodes)-1):
            n1 = nodes.get(way_nodes[i])
            n2 = nodes.get(way_nodes[i+1])
            if n1 and n2:
                length += haversine(n1['lat'], n1['lon'], n2['lat'], n2['lon'])
        
        if length < 0.1: continue # Skip very short segments
        
        # Link to stations
        connected_stations = []
        for wn_id in way_nodes:
            if wn_id in station_osm_ids:
                connected_stations.append(station_osm_ids[wn_id])
        
        if not connected_stations:
             # Find nearest station to endpoints
             for n_end in [start_node, end_node]:
                 min_dist = 999
                 best_s = 0
                 for s in scenario['stations']:
                     if 'lat' in s:
                         d = haversine(n_end['lat'], n_end['lon'], s['lat'], s['lon'])
                         if d < min_dist:
                             min_dist = d
                             best_s = s['id']
                 connected_stations.append(best_s)

        if len(connected_stations) < 2:
            connected_stations.append((connected_stations[0]+1)%max(1, len(scenario['stations'])))

        track_id = len(scenario['tracks'])
        scenario['tracks'].append({
            "id": track_id,
            "length_km": round(length, 2),
            "capacity": int(way.get('tags', {}).get('tracks', 1)),
            "is_single_track": way.get('tags', {}).get('railway:traffic_mode') == 'single' or int(way.get('tags', {}).get('tracks', 1)) == 1,
            "station_ids": list(set(connected_stations[:2]))
        })
        
    # 3. Inject synthetic traffic (Max 100 trains)
    num_trains = min(100, len(scenario['tracks']) // 2)
    track_ids = [t['id'] for t in scenario['tracks']]
    station_ids = [s['id'] for s in scenario['stations']]
    
    if track_ids and station_ids:
        for i in range(num_trains):
            scenario['trains'].append({
                "id": i,
                "current_track": random.choice(track_ids),
                "position_km": 0.0,
                "destination_station": random.choice(station_ids),
                "priority": random.randint(1, 10),
                "velocity_kmh": random.choice([100, 120, 160, 200]),
                "planned_route": []
            })

    with open(out_file, 'w') as f:
        json.dump(scenario, f, indent=2)
    logger.info(f"Scenario saved to {out_file} with {len(scenario['tracks'])} tracks.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--area", type=str, default="Lombardia", help="OSM Area name")
    parser.add_argument("--output", type=str, default="scenarios/lombardy_real.json")
    
    args = parser.parse_args()
    
    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    
    data = fetch_railway_data(args.area)
    if data:
        process_to_scenario(data, args.output)
