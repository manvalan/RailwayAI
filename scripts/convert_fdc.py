
import json

def convert_and_clean(input_path, output_path):
    with open(input_path, 'r') as f:
        data = json.load(f)
    
    # Extract infrastructure
    nodes = data.get('network', {}).get('nodes', [])
    edges = data.get('network', {}).get('edges', [])
    
    # Convert nodes to stations
    stations = []
    for node in nodes:
        stations.append({
            "id": node.get('id'),
            "name": node.get('name'),
            "num_platforms": node.get('platforms', 2),
            "lat": node.get('latitude', 0.0),
            "lon": node.get('longitude', 0.0)
        })
        
    # Convert edges to tracks
    tracks = []
    for edge in edges:
        # The AI expects numeric IDs or strings. We keep the ID as is.
        # But we need to map station IDs.
        tracks.append({
            "id": edge.get('id'),
            "length_km": edge.get('distance', 1.0),
            "capacity": edge.get('capacity', 1),
            "is_single_track": edge.get('trackType') == "single",
            "station_ids": [edge.get('from'), edge.get('to')]
        })
    
    # Clean scenario: No trains (or just the skeletal ones if needed)
    # The user said "clean it", so we start with an empty schedule.
    # The AI training script will generate/optimize new ones.
    scenario = {
        "stations": stations,
        "tracks": tracks,
        "trains": []
    }
    
    with open(output_path, 'w') as f:
        json.dump(scenario, f, indent=2)
    
    print(f"Converted {len(stations)} stations and {len(tracks)} tracks to {output_path}")

if __name__ == "__main__":
    convert_and_clean('/Users/michelebigi/Documents/FdC/rete-v2.rail', '/Users/michelebigi/RailwayAI/scenarios/fdc_scenario.json')
