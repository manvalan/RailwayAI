import json
import uuid
import datetime
from pathlib import Path

def convert_rail_to_scenario(rail_path, output_path):
    with open(rail_path, 'r') as f:
        data = json.load(f)

    network = data.get('network', {})
    
    # --- 1. Map Stations UUID -> Integer ID ---
    station_map = {} # UUID -> Integer ID
    stations_list = []
    
    # We need to find stations. In FDC format they might be in 'nodes' or implicitly referenced.
    # Looking at the snippet, they seem to be referenced by UUID like "STATION_055".
    # Let's verify if there is a "stations" or "nodes" key in the full file.
    # Based on the snippet, there is a "nodes" array in the network object (implied by typical graph structures).
    # Since I only saw "trains" and "edges" in the snippet, I will infer stations from edges endpoints.
    
    raw_nodes = network.get('nodes', [])
    if not raw_nodes:
        # Fallback: extract unique station IDs from edges and stops
        station_ids = set()
        for edge in network.get('edges', []):
            station_ids.add(edge.get('from'))
            station_ids.add(edge.get('to'))
        
        # Also check train stops
        for train in network.get('trains', []):
            for stop in train.get('stops', []):
                station_ids.add(stop.get('stationId'))
                
        # Create sorted list for deterministic IDs
        sorted_ids = sorted(list(station_ids))
        for i, sid in enumerate(sorted_ids):
            station_map[sid] = i
            stations_list.append({
                "id": i,
                "name": sid, # Use UUID as name initially, or lookup if available
                "num_platforms": 2, # Default
                "lat": 0.0,
                "lon": 0.0
            })
    else:
        for i, node in enumerate(raw_nodes):
            sid = node.get('id')
            station_map[sid] = i
            stations_list.append({
                "id": i,
                "name": node.get('name', sid),
                "num_platforms": node.get('platforms', 2),
                "lat": 0.0,
                "lon": 0.0
            })

    # --- 2. Convert Edges to Tracks ---
    tracks_list = []
    edges = network.get('edges', [])
    
    for i, edge in enumerate(edges):
        from_id = edge.get('from')
        to_id = edge.get('to')
        
        if from_id not in station_map or to_id not in station_map:
            continue
            
        tracks_list.append({
            "id": i,
            "length_km": edge.get('distance', 1.0),
            "capacity": edge.get('capacity', 1),
            "is_single_track": edge.get('trackType', 'single') == 'single',
            "station_ids": [station_map[from_id], station_map[to_id]]
        })

    # --- 3. Convert Trains ---
    trains_list = []
    raw_trains = network.get('trains', [])
    
    for i, t in enumerate(raw_trains):
        # Determine starting track (first stop)
        stops = t.get('stops', [])
        start_track = 0
        if stops:
            first_station = stops[0].get('stationId')
            # Find a track connected to this station
            if first_station in station_map:
                st_id = station_map[first_station]
                for trk in tracks_list:
                    if st_id in trk['station_ids']:
                        start_track = trk['id']
                        break
        
        trains_list.append({
            "id": i,
            "original_id": t.get('id'),
            "name": t.get('name'),
            "current_track": start_track,
            "position_km": 0.0,
            "destination_station": 0, # Placeholder
            "priority": t.get('priority', 5),
            "velocity_kmh": t.get('maxSpeed', 120),
            "planned_route": [] # Logic to calculate route could be added
        })

    # --- Final Output ---
    output_data = {
        "stations": stations_list,
        "tracks": tracks_list,
        "trains": trains_list
    }
    
    with open(output_path, 'w') as f:
        json.dump(output_data, f, indent=2)
    
    print(f"Converted {len(trains_list)} trains, {len(tracks_list)} tracks, {len(stations_list)} stations.")

if __name__ == "__main__":
    rail_file = "/Users/michelebigi/Documents/FdC/Scenari/FDC Network.rail"
    json_file = "/Users/michelebigi/RailwayAI/scenarios/fdc_scenario.json"
    try:
        convert_rail_to_scenario(rail_file, json_file)
    except Exception as e:
        print(f"Error: {e}")
