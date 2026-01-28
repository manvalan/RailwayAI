import json
import os
import sys

def convert_fdc_to_railway(input_file, output_file):
    print(f"Reading FDC schema from {input_file}...")
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            # Remove potential junk at end
            if content.endswith('ù'):
                content = content[:-1]
            data = json.loads(content)
    except Exception as e:
        print(f"Error reading JSON: {e}")
        return

    # 1. Process Nodes -> Stations
    stations = []
    for node in data.get('nodes', []):
        stations.append({
            "id": node['id'],
            "name": node.get('name', f"Station {node['id']}"),
            "num_platforms": node.get('num_platforms', 2) # Default 2
        })

    # 2. Process Links -> Tracks
    # Group by station pair to detect bidirectional tracks
    links_by_pair = {}
    
    for link in data.get('links', []):
        pair = tuple(sorted([link['source'], link['target']]))
        if pair not in links_by_pair:
            links_by_pair[pair] = []
        links_by_pair[pair].append(link)

    tracks = []
    track_id_counter = 1000
    
    for pair, links in links_by_pair.items():
        # If there are 2 links between the same stations, it might be:
        # A) Two directions of a single track
        # B) A true double track line
        
        # Simplified logic: 
        # - If 1 link: Single track, capacity 1
        # - If 2 links: Double track, capacity 2 (or 1 if it was just A->B and B->A on one physical track)
        
        # We'll assume if there are 2 links, it's a double track line (common for FDC)
        # unless user specifies otherwise. Let's make it smarter:
        # Check if they have same length etc.
        
        is_single = len(links) == 1
        
        # Calculate length (average if multiple)
        length = sum(l.get('length_km', 0) for l in links) / len(links)
        
        tracks.append({
            "id": track_id_counter,
            "station_ids": list(pair),
            "length_km": round(length, 3),
            "is_single_track": is_single,
            "capacity": 2 if not is_single else 1
        })
        track_id_counter += 1

    # 3. Create basic trains if not present
    trains = data.get('trains', [])
    # (If we wanted to automate train path updating, we'd need a map of old link IDs to new track IDs)
    # But FDC links often don't have paths yet.

    output_data = {
        "stations": stations,
        "tracks": tracks,
        "trains": trains,
        "max_iterations": data.get('max_iterations', 1440),
        "ga_max_iterations": data.get('ga_max_iterations', 200)
    }

    print(f"Writing Railway AI format to {output_file}...")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2)
    
    print("Done! Summary:")
    print(f"- Stations: {len(stations)}")
    print(f"- Processed Links: {len(data.get('links', []))}")
    print(f"- Unified Tracks: {len(tracks)}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python fdc_to_railway.py <input_fdc_json> [output_json]")
    else:
        inp = sys.argv[1]
        out = sys.argv[2] if len(sys.argv) > 2 else "converted_" + os.path.basename(inp)
        convert_fdc_to_railway(inp, out)
