#!/usr/bin/env python3
"""
Diagnostic script to analyze the railway network scenario and identify the problem.
"""

import json
import sys

def analyze_scenario(scenario_file):
    """Analyze the railway scenario to identify issues."""
    
    with open(scenario_file, 'r') as f:
        data = json.load(f)
    
    print("=" * 80)
    print("RAILWAY AI SOLVER DIAGNOSTIC ANALYSIS")
    print("=" * 80)
    print()
    
    # Analyze trains
    print("TRAIN ANALYSIS")
    print("-" * 80)
    trains = data['trains']
    for train in trains:
        print(f"Train {train['id']}:")
        print(f"  Current Track: {train['current_track']}")
        print(f"  Position: {train['position_km']} km")
        print(f"  Velocity: {train['velocity_kmh']} km/h")
        print(f"  Destination Station: {train['destination_station']}")
        print(f"  Priority: {train['priority']}")
        print(f"  Delayed: {train['is_delayed']} ({train['delay_minutes']} min)")
        print()
    
    # Analyze tracks
    print("\nTRACK ANALYSIS")
    print("-" * 80)
    track_dict = {t['id']: t for t in data['tracks']}
    
    # Check tracks where trains are located
    for train in trains:
        track_id = train['current_track']
        if track_id in track_dict:
            track = track_dict[track_id]
            print(f"Track {track_id} (Train {train['id']} is here):")
            print(f"  Length: {track['length_km']} km")
            print(f"  Single Track: {track['is_single_track']}")
            print(f"  Capacity: {track['capacity']}")
            print(f"  Connects Stations: {track['station_ids']}")
            print()
    
    # CRITICAL ISSUE DETECTION
    print("\nCRITICAL ISSUE DETECTION")
    print("-" * 80)
    
    # Issue 1: Check if trains are on the same track
    train_tracks = {}
    for train in trains:
        track_id = train['current_track']
        if track_id not in train_tracks:
            train_tracks[track_id] = []
        train_tracks[track_id].append(train)
    
    conflicts_found = False
    for track_id, track_trains in train_tracks.items():
        if len(track_trains) > 1:
            print(f"⚠️  CONFLICT: Multiple trains on track {track_id}")
            track = track_dict[track_id]
            print(f"   Track is {'SINGLE' if track['is_single_track'] else 'DOUBLE'}, Capacity: {track['capacity']}")
            for train in track_trains:
                print(f"   - Train {train['id']}: pos={train['position_km']}km, vel={train['velocity_kmh']}km/h")
            
            # Check for head-on collision
            if track['is_single_track'] and len(track_trains) == 2:
                t1, t2 = track_trains[0], track_trains[1]
                if (t1['velocity_kmh'] > 0 and t2['velocity_kmh'] < 0) or \
                   (t1['velocity_kmh'] < 0 and t2['velocity_kmh'] > 0):
                    print(f"   🚨 HEAD-ON COLLISION RISK: Trains moving in opposite directions!")
                    
                    # Calculate meeting time
                    distance = abs(t1['position_km'] - t2['position_km'])
                    relative_speed = abs(t1['velocity_kmh']) + abs(t2['velocity_kmh'])
                    if relative_speed > 0:
                        meeting_time_hours = distance / relative_speed
                        meeting_time_minutes = meeting_time_hours * 60
                        print(f"   ⏱️  Estimated collision in {meeting_time_minutes:.2f} minutes")
            conflicts_found = True
            print()
    
    # Issue 2: Check destination reachability
    print("\nDESTINATION REACHABILITY ANALYSIS")
    print("-" * 80)
    
    station_dict = {s['id']: s for s in data['stations']}
    
    for train in trains:
        dest_station = train['destination_station']
        current_track = train['current_track']
        
        if dest_station not in station_dict:
            print(f"❌ Train {train['id']}: Destination station {dest_station} does not exist!")
            continue
        
        if current_track not in track_dict:
            print(f"❌ Train {train['id']}: Current track {current_track} does not exist!")
            continue
        
        track = track_dict[current_track]
        dest_name = station_dict[dest_station]['name']
        
        print(f"Train {train['id']} → Destination: {dest_name} (Station {dest_station})")
        print(f"  Current track {current_track} connects: {track['station_ids']}")
        
        if dest_station in track['station_ids']:
            print(f"  ✅ Destination is on current track")
        else:
            print(f"  ⚠️  Destination NOT on current track - needs route planning")
        print()
    
    # Issue 3: Check for impossible states
    print("\nSTATE VALIDATION")
    print("-" * 80)
    
    for train in trains:
        track = track_dict.get(train['current_track'])
        if track:
            if train['position_km'] < 0:
                print(f"❌ Train {train['id']}: Negative position ({train['position_km']} km)")
            elif train['position_km'] > track['length_km']:
                print(f"❌ Train {train['id']}: Position ({train['position_km']} km) exceeds track length ({track['length_km']} km)")
            else:
                print(f"✅ Train {train['id']}: Position is valid")
    
    print()
    print("=" * 80)
    print("DIAGNOSIS SUMMARY")
    print("=" * 80)
    
    if not conflicts_found:
        print("✅ No immediate conflicts detected")
        print()
        print("POSSIBLE REASONS WHY AI IS NOT SOLVING:")
        print("1. The scenario may be too simple (only 2 trains, no actual conflict)")
        print("2. The ML model may not be loaded properly")
        print("3. The conflict detection logic may have bugs")
        print("4. The trains may not actually be in conflict on their current paths")
    else:
        print("⚠️  Conflicts detected - AI should be resolving these!")
        print()
        print("POSSIBLE REASONS WHY AI IS NOT SOLVING:")
        print("1. ML model not loaded - check MODEL_PATH environment variable")
        print("2. Conflict detection logic not triggering properly")
        print("3. Resolution logic not finding alternative tracks")
        print("4. API request format mismatch")
    
    print()
    return conflicts_found

if __name__ == "__main__":
    scenario_file = sys.argv[1] if len(sys.argv) > 1 else "test_scenario.json"
    analyze_scenario(scenario_file)
