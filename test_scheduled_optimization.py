"""
Test script for the new scheduled train optimization endpoint.
Tests the Bywater-Nobottle opposite trains scenario.
"""

import requests
import json

# API configuration
API_BASE = "http://localhost:8002"
USERNAME = "admin"
PASSWORD = "admin"

def get_token():
    """Get authentication token"""
    response = requests.post(
        f"{API_BASE}/token",
        data={"username": USERNAME, "password": PASSWORD}
    )
    response.raise_for_status()
    return response.json()["access_token"]

def test_bywater_nobottle_scenario():
    """Test the Bywater-Nobottle opposite trains scenario"""
    
    print("=" * 80)
    print("Testing Bywater-Nobottle Opposite Trains Scenario")
    print("=" * 80)
    print()
    
    # Get authentication token
    print("1. Authenticating...")
    token = get_token()
    print("   ✓ Token obtained")
    print()
    
    # Prepare request
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    # Simplified scenario with key stations and tracks
    scenario = {
        "trains": [
            {
                "id": 0,
                "origin_station": 11,  # Bywater
                "destination_station": 1,  # Nobottle
                "scheduled_departure_time": "12:00:00",
                "velocity_kmh": 160,
                "priority": 5,
                "position_km": 0,
                "current_track": 18,  # Will be auto-planned
                "is_delayed": False,
                "delay_minutes": 0
            },
            {
                "id": 1,
                "origin_station": 1,  # Nobottle
                "destination_station": 11,  # Bywater
                "scheduled_departure_time": "12:00:00",
                "velocity_kmh": 160,
                "priority": 5,
                "position_km": 0,
                "current_track": 1,  # Will be auto-planned
                "is_delayed": False,
                "delay_minutes": 0
            }
        ],
        "stations": [
            {"id": 1, "name": "Nobottle", "num_platforms": 2},
            {"id": 11, "name": "Bywater", "num_platforms": 4},
            {"id": 42, "name": "Little Delvings", "num_platforms": 2},
            {"id": 43, "name": "Gamwich", "num_platforms": 2},
            {"id": 44, "name": "Tightfield", "num_platforms": 2},
            {"id": 51, "name": "Withwell", "num_platforms": 2},
            {"id": 52, "name": "Tuck", "num_platforms": 2}
        ],
        "tracks": [
            {"id": 1, "length_km": 24, "is_single_track": True, "capacity": 1, "station_ids": [1, 43]},
            {"id": 17, "length_km": 28, "is_single_track": False, "capacity": 2, "station_ids": [11, 52]},
            {"id": 18, "length_km": 84, "is_single_track": False, "capacity": 2, "station_ids": [11, 26]},
            {"id": 56, "length_km": 23, "is_single_track": True, "capacity": 1, "station_ids": [42, 41]},
            {"id": 58, "length_km": 22, "is_single_track": True, "capacity": 1, "station_ids": [42, 44]},
            {"id": 59, "length_km": 22, "is_single_track": True, "capacity": 1, "station_ids": [43, 44]},
            {"id": 64, "length_km": 14, "is_single_track": True, "capacity": 1, "station_ids": [50, 51]},
            {"id": 65, "length_km": 10, "is_single_track": True, "capacity": 1, "station_ids": [51, 52]},
            {"id": 66, "length_km": 0.3, "is_single_track": True, "capacity": 1, "station_ids": [52, 56]}
        ],
        "max_iterations": 60  # 60 minute time horizon
    }
    
    print("2. Sending optimization request...")
    print(f"   - Train 0: Bywater → Nobottle @ 12:00")
    print(f"   - Train 1: Nobottle → Bywater @ 12:00")
    print(f"   - Time horizon: 60 minutes")
    print()
    
    # Send request to new endpoint
    response = requests.post(
        f"{API_BASE}/api/v1/optimize_scheduled",
        headers=headers,
        json=scenario
    )
    
    if response.status_code != 200:
        print(f"   ✗ Request failed: {response.status_code}")
        print(f"   Error: {response.text}")
        return
    
    result = response.json()
    
    print("3. Optimization Results")
    print("=" * 80)
    print(f"   Success: {result['success']}")
    print(f"   Conflicts Detected: {result['conflicts_detected']}")
    print(f"   Conflicts Resolved: {result['conflicts_resolved']}")
    print(f"   Total Delay: {result['total_delay_minutes']:.1f} minutes")
    print(f"   Inference Time: {result['inference_time_ms']:.2f} ms")
    print()
    
    if result['resolutions']:
        print("4. Recommended Resolutions")
        print("-" * 80)
        for i, resolution in enumerate(result['resolutions'], 1):
            print(f"   Resolution {i}:")
            print(f"     Train ID: {resolution['train_id']}")
            print(f"     Delay: {resolution['time_adjustment_min']:.1f} minutes")
            print(f"     Track: {resolution['track_assignment']}")
            print(f"     Confidence: {resolution['confidence']:.2%}")
            print()
    else:
        print("4. No conflicts detected - trains can depart as scheduled!")
        print()
    
    print("=" * 80)
    print("Test completed successfully!")
    print("=" * 80)

if __name__ == "__main__":
    try:
        test_bywater_nobottle_scenario()
    except requests.exceptions.ConnectionError:
        print("ERROR: Could not connect to API server.")
        print("Make sure the server is running: python api/server.py")
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
