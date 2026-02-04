import requests
import json
import argparse
import logging
import math
import random
import os
import sys

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

COUNTRY_MAPPING = {
    "italia": "Italy",
    "francia": "France",
    "spagna": "Spain",
    "germania": "Germany",
    "belgio": "Belgium",
    "olanda": "Netherlands",
    "svizzera": "Switzerland",
    "inghilterra": "United Kingdom",
    "regno unito": "United Kingdom"
}

def fetch_railway_data(area_name: str):
    """
    Queries Overpass API for railway infrastructure in a specific area.
    """
    # Normalize area name
    normalized_area = COUNTRY_MAPPING.get(area_name.lower(), area_name)
    logger.info(f"Fetching railway data for: {normalized_area}")
    
    # Increase timeout for countries and filter by main lines to avoid overload
    query = f"""
    [out:json][timeout:300];
    area[name="{normalized_area}"]->.searchArea;
    (
      way["railway"="rail"]["usage"~"main|regional|high_speed|suburban|branch"](area.searchArea);
      node["railway"="station"](area.searchArea);
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
            
    if not scenario['stations']:
        logger.warning("No stations found. Creating dummy endpoints.")
        scenario['stations'].append({"id": 0, "name": "Source", "num_platforms": 2, "lat": 45.0, "lon": 9.0})
        scenario['stations'].append({"id": 1, "name": "Sink", "num_platforms": 2, "lat": 45.1, "lon": 9.1})

    station_osm_ids = {s['osm_id']: s['id'] for s in scenario['stations'] if 'osm_id' in s}
    all_station_ids = [s['id'] for s in scenario['stations']]

    # 2. Process Tracks (Ways)
    # We need to find which stations each way passes through
    station_osm_to_id = {s['osm_id']: s['id'] for s in scenario['stations'] if 'osm_id' in s}
    
    for way in ways:
        way_nodes = way.get('nodes', [])
        if len(way_nodes) < 2: continue
        
        # Find all stations along this way
        stations_on_way = []
        for i, node_id in enumerate(way_nodes):
            if node_id in station_osm_to_id:
                stations_on_way.append((i, station_osm_to_id[node_id]))
        
        # If the way doesn't have at least 2 stations, try to find the nearest for endpoints
        # BUT only if the distance is reasonable (< 500m)
        if len(stations_on_way) < 2:
            endpoint_stations = []
            for node_idx in [0, -1]:
                n_id = way_nodes[node_idx]
                node_data = nodes.get(n_id)
                if not node_data: continue
                
                min_dist = 0.5 # 500 meters max for "snapping"
                best_s = -1
                for s in scenario['stations']:
                    d = haversine(node_data['lat'], node_data['lon'], s['lat'], s['lon'])
                    if d < min_dist:
                        min_dist = d
                        best_s = s['id']
                
                if best_s != -1:
                    # Update stations_on_way if not already there
                    if not any(s[1] == best_s for s in stations_on_way):
                        stations_on_way.append((node_idx, best_s))
            
            # Sort by index to keep topology
            stations_on_way.sort()

        # If we still don't have 2 stations, this track is a "floating" segment.
        # In a real rail network, we might want to keep it, but for a simplified graph,
        # we only care about connections between stations.
        if len(stations_on_way) < 2:
            continue

        # Create tracks between consecutive stations found on this way
        for i in range(len(stations_on_way) - 1):
            idx1, s1_id = stations_on_way[i]
            idx2, s2_id = stations_on_way[i+1]
            
            if s1_id == s2_id: continue
            
            # Calculate segment length
            segment_length = 0
            for j in range(idx1, idx2):
                n1 = nodes.get(way_nodes[j])
                n2 = nodes.get(way_nodes[j+1])
                if n1 and n2:
                    segment_length += haversine(n1['lat'], n1['lon'], n2['lat'], n2['lon'])
            
            if segment_length < 0.05: continue 
            
            track_id = len(scenario['tracks'])
            scenario['tracks'].append({
                "id": track_id,
                "length_km": round(segment_length, 2),
                "capacity": int(way.get('tags', {}).get('tracks', 1)),
                "is_single_track": way.get('tags', {}).get('railway:traffic_mode') == 'single' or int(way.get('tags', {}).get('tracks', 1)) == 1,
                "station_ids": [s1_id, s2_id]
            })
        
    # 3. Inject synthetic traffic
    num_trains = min(100, len(scenario['tracks']) // 2)
    track_ids = [t['id'] for t in scenario['tracks']]
    
    if track_ids and all_station_ids:
        for i in range(num_trains):
            scenario['trains'].append({
                "id": i,
                "current_track": random.choice(track_ids),
                "position_km": 0.0,
                "destination_station": random.choice(all_station_ids),
                "priority": random.randint(1, 10),
                "velocity_kmh": random.choice([100, 120, 160, 200]),
                "planned_route": []
            })

    with open(out_file, 'w') as f:
        json.dump(scenario, f, indent=2)
    logger.info(f"Scenario saved to {out_file} with {len(scenario['tracks'])} tracks and {len(scenario['trains'])} trains.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--area", type=str, default="Lombardia", help="OSM Area name")
    parser.add_argument("--output", type=str, default="scenarios/lombardy_real.json")
    
    args = parser.parse_args()
    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    
    data = fetch_railway_data(args.area)
    if data and data.get('elements'):
        process_to_scenario(data, args.output)
        if not os.path.exists(args.output):
            logger.error("Failed to create output file.")
            sys.exit(1)
    else:
        logger.error(f"No railway data found for area: {args.area}")
        sys.exit(1)
