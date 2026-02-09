
import json
import math
import os

def haversine(lat1, lon1, lat2, lon2):
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return R * c

def refine_scenario(input_path, output_path):
    with open(input_path, 'r') as f:
        data = json.load(f)
    
    stations = data['stations']
    tracks = data['tracks']
    
    # 1. Create a map of station pairs to their shortest original track
    pair_to_track = {}
    for t in tracks:
        pair = tuple(sorted(t['station_ids']))
        if pair not in pair_to_track or t['length_km'] < pair_to_track[pair]['length_km']:
            pair_to_track[pair] = t

    # 2. Heuristic: For each station, we only want to connect to its closest neighbors
    # that don't have another station "blocking" the path.
    # We'll use a simple proximity-based filtering.
    
    final_tracks = []
    processed_pairs = set()

    for i, s1 in enumerate(stations):
        # Find all other stations and sort them by distance
        neighbors = []
        for j, s2 in enumerate(stations):
            if i == j: continue
            dist = haversine(s1['lat'], s1['lon'], s2['lat'], s2['lon'])
            neighbors.append((j, dist))
        
        neighbors.sort(key=lambda x: x[1])
        
        # We take the N closest neighbors that are physically connected in the original data
        # Typically 1 or 2 neighbors for a line, maybe 3-4 for a hub like Empoli or Firenze SMN.
        added_count = 0
        for neighbor_idx, dist in neighbors:
            pair = tuple(sorted((s1['id'], stations[neighbor_idx]['id'])))
            if pair in processed_pairs: continue
            
            # Check if there was an original track for this pair
            if pair in pair_to_track:
                original_track = pair_to_track[pair]
                
                # CRITICAL: Only add if the distance is "short" (direct adjacency)
                # On the Siena-Empoli line, stations are usually 4-12km apart.
                # If the distance is > 15km, it's likely a skip-track (e.g. Siena -> Poggibonsi skipping Badesse)
                if dist < 15.0:
                    final_tracks.append({
                        "id": len(final_tracks),
                        "length_km": original_track['length_km'],
                        "capacity": original_track['capacity'],
                        "is_single_track": original_track['is_single_track'],
                        "station_ids": [s1['id'], stations[neighbor_idx]['id']]
                    })
                    processed_pairs.add(pair)
                    added_count += 1
            
            # Hubs like Empoli can have more connections, but usually 3 is the max for a standard line junction
            if added_count >= 3: break

    # 3. Clean trains (we will recreate them later with realistic data)
    data['tracks'] = final_tracks
    data['trains'] = [] # Clear for now to focus on infrastructure
    
    with open(output_path, 'w') as f:
        json.dump(data, f, indent=2)
    
    print(f"Refined scenario: {len(stations)} stations, {len(final_tracks)} tracks. Saved to {output_path}")

if __name__ == "__main__":
    refine_scenario('scenarios/siena_empoli_real.json', 'scenarios/siena_empoli_clean.json')
