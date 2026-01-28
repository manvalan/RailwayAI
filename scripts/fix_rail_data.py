import json
import os
import sys

def fix_rail_data(input_file, output_file):
    print(f"Reading {input_file}...")
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            # Remove potential trailing junk (like the 'ù' mentioned)
            if content.endswith('ù'):
                content = content[:-1]
            data = json.loads(content)
    except Exception as e:
        print(f"Error reading JSON: {e}")
        return

    # 1. Normalize Tracks
    unique_tracks = {}
    track_mapping = {} # Old ID -> New ID
    
    # Sort tracks to identify duplicates (station_ids [0,2] is same as [2,0])
    for track in data.get('tracks', []):
        stations = sorted(track['station_ids'])
        key = tuple(stations)
        
        if key not in unique_tracks:
            # First time we see this connection
            # Add missing capacity if not present
            if 'capacity' not in track:
                track['capacity'] = 1 if track.get('is_single_track', True) else 2
            
            # Remove non-model fields or ensure they are present
            cleaned_track = {
                "id": track['id'],
                "length_km": track['length_km'],
                "is_single_track": track.get('is_single_track', True),
                "capacity": track['capacity'],
                "station_ids": track['station_ids']
            }
            unique_tracks[key] = cleaned_track
            track_mapping[track['id']] = track['id']
        else:
            # Duplicate connection (different direction/ID)
            # Map the duplicate ID to the first one we found
            existing_track = unique_tracks[key]
            track_mapping[track['id']] = existing_track['id']
            print(f"Mapping duplicate track {track['id']} ({track['station_ids']}) to {existing_track['id']}")

    # 2. Update Trains
    fixed_trains = []
    for train in data.get('trains', []):
        # Ensure ID is integer
        try:
            train_id = int(train.get('id', 0))
        except:
            train_id = 0
            
        # Update current track and planned route using mapping
        current_track = track_mapping.get(train.get('current_track'), train.get('current_track'))
        
        planned_route = train.get('planned_route')
        if planned_route:
            planned_route = [track_mapping.get(tid, tid) for tid in planned_route]
        
        # Build clean train object based on server model
        fixed_train = {
            "id": train_id,
            "position_km": float(train.get('position_km', 0.0)),
            "velocity_kmh": float(train.get('velocity_kmh', 0.0)),
            "current_track": current_track,
            "destination_station": int(train.get('destination_station', 0)),
            "delay_minutes": float(train.get('delay_minutes', 0.0)),
            "priority": int(train.get('priority', 5)),
            "is_delayed": bool(train.get('is_delayed', False)),
            "origin_station": train.get('origin_station'),
            "scheduled_departure_time": train.get('scheduled_departure_time'),
            "planned_route": planned_route,
            "current_route_index": int(train.get('current_route_index', 0))
        }
        fixed_trains.append(fixed_train)

    # 3. Rebuild Final Data
    data['tracks'] = list(unique_tracks.values())
    data['trains'] = fixed_trains
    
    # Ensure other root fields exist
    if 'stations' not in data:
        data['stations'] = []
    if 'max_iterations' not in data:
        data['max_iterations'] = 1440
    if 'ga_max_iterations' not in data:
        data['ga_max_iterations'] = 200

    print(f"Writing fixed data to {output_file}...")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)
    
    print("Done! Summary:")
    print(f"- Original tracks: {len(data.get('tracks', [])) + len(track_mapping) - len(unique_tracks)}")
    print(f"- Unique tracks: {len(unique_tracks)}")
    print(f"- Fixed trains: {len(fixed_trains)}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python fix_rail_data.py <input_json> [output_json]")
    else:
        inp = sys.argv[1]
        out = sys.argv[2] if len(sys.argv) > 2 else "fixed_" + inp
        fix_rail_data(inp, out)
