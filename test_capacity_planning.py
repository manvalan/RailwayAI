"""
Test script for the capacity planning endpoint.
Tests the /api/v1/suggest_schedule endpoint with various scenarios.
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

def test_capacity_planning():
    """Test capacity planning with a simple scenario"""
    
    print("=" * 80)
    print("Testing Capacity Planning - Schedule Suggestion")
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
    
    # Simple scenario: 5 trains to schedule over 8 hours
    scenario = {
        "trains": [
            {
                "id": 0,
                "origin_station": 11,
                "destination_station": 26,
                "velocity_kmh": 160,
                "priority": 5,
                "position_km": 0,
                "current_track": 18,
                "delay_minutes": 0,
                "is_delayed": False
            },
            {
                "id": 1,
                "origin_station": 26,
                "destination_station": 11,
                "velocity_kmh": 150,
                "priority": 5,
                "position_km": 0,
                "current_track": 18,
                "delay_minutes": 0,
                "is_delayed": False
            },
            {
                "id": 2,
                "origin_station": 11,
                "destination_station": 26,
                "velocity_kmh": 140,
                "priority": 3,
                "position_km": 0,
                "current_track": 18,
                "delay_minutes": 0,
                "is_delayed": False
            },
            {
                "id": 3,
                "origin_station": 26,
                "destination_station": 11,
                "velocity_kmh": 160,
                "priority": 7,
                "position_km": 0,
                "current_track": 18,
                "delay_minutes": 0,
                "is_delayed": False
            },
            {
                "id": 4,
                "origin_station": 11,
                "destination_station": 26,
                "velocity_kmh": 155,
                "priority": 5,
                "position_km": 0,
                "current_track": 18,
                "delay_minutes": 0,
                "is_delayed": False
            }
        ],
        "tracks": [
            {"id": 18, "length_km": 84, "is_single_track": False, "capacity": 2, "station_ids": [11, 26]}
        ],
        "stations": [
            {"id": 11, "name": "Bywater", "num_platforms": 4},
            {"id": 26, "name": "Brandy Hall", "num_platforms": 4}
        ],
        "time_window": {
            "start": "06:00:00",
            "end": "14:00:00"
        },
        "target_capacity_utilization": 0.66,
        "optimization_params": {
            "max_iterations": 500,
            "population_size": 30,
            "mutation_rate": 0.15
        }
    }
    
    print("2. Sending capacity planning request...")
    print(f"   - Trains: {len(scenario['trains'])}")
    print(f"   - Time window: {scenario['time_window']['start']} - {scenario['time_window']['end']}")
    print(f"   - Target utilization: {scenario['target_capacity_utilization']:.0%}")
    print(f"   - Max iterations: {scenario['optimization_params']['max_iterations']}")
    print()
    
    # Send request
    response = requests.post(
        f"{API_BASE}/api/v1/suggest_schedule",
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
    print(f"   Iterations: {result['optimization_info']['iterations']}")
    print(f"   Computation time: {result['optimization_info']['computation_time_ms']:.2f} ms")
    print(f"   Convergence score: {result['optimization_info']['convergence_score']:.4f}")
    print()
    
    print("4. Network Metrics")
    print("-" * 80)
    metrics = result['network_metrics']
    print(f"   Average capacity utilization: {metrics['average_capacity_utilization']:.2%}")
    print(f"   Peak capacity utilization: {metrics['peak_capacity_utilization']:.2%}")
    print(f"   Total conflicts: {metrics['total_conflicts']}")
    print(f"   Temporal distribution score: {metrics['temporal_distribution_score']:.2%}")
    print()
    
    print("5. Suggested Schedule")
    print("-" * 80)
    for train in result['suggested_schedule']:
        print(f"   Train {train['train_id']}: Depart at {train['suggested_departure_time']}")
        print(f"     Route: {train['route']}")
        print(f"     Conflicts: {train['conflicts']}")
        print()
    
    print("6. Track Utilization")
    print("-" * 80)
    for track in result['track_utilization']:
        bottleneck = " [BOTTLENECK]" if track['is_bottleneck'] else ""
        print(f"   Track {track['track_id']}: {track['utilization']:.2%} utilization{bottleneck}")
        print(f"     Theoretical capacity: {track['theoretical_capacity']:.1f}")
        print(f"     Demand: {track['demand']}")
        print()
    
    print("=" * 80)
    print("Test completed successfully!")
    print("=" * 80)

if __name__ == "__main__":
    try:
        test_capacity_planning()
    except requests.exceptions.ConnectionError:
        print("ERROR: Could not connect to API server.")
        print("Make sure the server is running: python api/server.py")
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
