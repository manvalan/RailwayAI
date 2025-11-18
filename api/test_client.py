"""
Test client for Railway AI Scheduler REST API

Demonstrates how to interact with the API endpoints.
"""

import requests
import json
from typing import List, Dict

API_BASE_URL = "http://localhost:8000"


def test_health_check():
    """Test health check endpoint"""
    print("\n" + "="*70)
    print("  Testing Health Check")
    print("="*70)
    
    response = requests.get(f"{API_BASE_URL}/api/v1/health")
    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    
    return response.status_code == 200


def test_model_info():
    """Test model info endpoint"""
    print("\n" + "="*70)
    print("  Testing Model Info")
    print("="*70)
    
    response = requests.get(f"{API_BASE_URL}/api/v1/model/info")
    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    
    return response.status_code == 200


def test_metrics():
    """Test metrics endpoint"""
    print("\n" + "="*70)
    print("  Testing Metrics")
    print("="*70)
    
    response = requests.get(f"{API_BASE_URL}/api/v1/metrics")
    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    
    return response.status_code == 200


def test_optimize_simple():
    """Test optimization with simple scenario"""
    print("\n" + "="*70)
    print("  Testing Simple Optimization")
    print("="*70)
    
    # Simple scenario: 2 trains, potential conflict
    request_data = {
        "trains": [
            {
                "id": 101,
                "position_km": 15.0,
                "velocity_kmh": 120.0,
                "current_track": 1,
                "destination_station": 3,
                "delay_minutes": 5.0,
                "priority": 8,
                "is_delayed": True
            },
            {
                "id": 102,
                "position_km": 45.0,
                "velocity_kmh": 100.0,
                "current_track": 1,
                "destination_station": 2,
                "delay_minutes": 0.0,
                "priority": 5,
                "is_delayed": False
            }
        ],
        "max_iterations": 100
    }
    
    print(f"\nSending {len(request_data['trains'])} trains for optimization...")
    
    response = requests.post(
        f"{API_BASE_URL}/api/v1/optimize",
        json=request_data,
        headers={"Content-Type": "application/json"}
    )
    
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        print(f"\nOptimization Result:")
        print(f"  Success: {result['success']}")
        print(f"  Inference Time: {result['inference_time_ms']:.2f} ms")
        print(f"  Total Delay: {result['total_delay_minutes']:.2f} min")
        print(f"  Conflicts Detected: {result['conflicts_detected']}")
        print(f"  Conflicts Resolved: {result['conflicts_resolved']}")
        print(f"  Resolutions: {len(result['resolutions'])}")
        
        for res in result['resolutions']:
            print(f"\n    Train {res['train_id']}:")
            print(f"      Time Adjustment: {res['time_adjustment_min']:.2f} min")
            print(f"      Track Assignment: {res['track_assignment']}")
            print(f"      Confidence: {res['confidence']:.2f}")
    else:
        print(f"Error: {response.text}")
    
    return response.status_code == 200


def test_optimize_complex():
    """Test optimization with complex scenario"""
    print("\n" + "="*70)
    print("  Testing Complex Optimization")
    print("="*70)
    
    # More complex scenario: multiple trains with delays
    trains = []
    for i in range(10):
        trains.append({
            "id": 200 + i,
            "position_km": float(i * 10 + 5),
            "velocity_kmh": 100.0 + (i % 3) * 20.0,
            "current_track": i % 3,
            "destination_station": (i + 3) % 5,
            "delay_minutes": float((i % 4) * 2.0),
            "priority": 5 + (i % 5),
            "is_delayed": (i % 3) == 0
        })
    
    request_data = {
        "trains": trains,
        "max_iterations": 100
    }
    
    print(f"\nSending {len(trains)} trains for optimization...")
    
    response = requests.post(
        f"{API_BASE_URL}/api/v1/optimize",
        json=request_data
    )
    
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        print(f"\nOptimization Result:")
        print(f"  Success: {result['success']}")
        print(f"  Inference Time: {result['inference_time_ms']:.2f} ms")
        print(f"  Total Delay: {result['total_delay_minutes']:.2f} min")
        print(f"  Resolutions: {len(result['resolutions'])}")
    else:
        print(f"Error: {response.text}")
    
    return response.status_code == 200


def benchmark_api(num_requests: int = 100):
    """Benchmark API performance"""
    print("\n" + "="*70)
    print(f"  Benchmarking API ({num_requests} requests)")
    print("="*70)
    
    request_data = {
        "trains": [
            {
                "id": i,
                "position_km": float(i * 5),
                "velocity_kmh": 120.0,
                "current_track": i % 2,
                "destination_station": (i + 2) % 3,
                "delay_minutes": 0.0,
                "priority": 5,
                "is_delayed": False
            }
            for i in range(5)
        ]
    }
    
    import time
    
    times = []
    successes = 0
    
    print(f"\nSending {num_requests} requests...")
    
    for i in range(num_requests):
        start = time.time()
        response = requests.post(
            f"{API_BASE_URL}/api/v1/optimize",
            json=request_data
        )
        end = time.time()
        
        if response.status_code == 200:
            successes += 1
            times.append((end - start) * 1000.0)
        
        if (i + 1) % 10 == 0:
            print(f"  Progress: {i+1}/{num_requests}")
    
    if times:
        avg_time = sum(times) / len(times)
        min_time = min(times)
        max_time = max(times)
        
        print(f"\nBenchmark Results:")
        print(f"  Total Requests: {num_requests}")
        print(f"  Successful: {successes}")
        print(f"  Failed: {num_requests - successes}")
        print(f"  Avg Response Time: {avg_time:.2f} ms")
        print(f"  Min Response Time: {min_time:.2f} ms")
        print(f"  Max Response Time: {max_time:.2f} ms")
        print(f"  Throughput: {1000.0/avg_time:.1f} requests/sec")


def main():
    """Run all tests"""
    print("\n" + "="*70)
    print("  Railway AI Scheduler - API Test Suite")
    print("="*70)
    
    try:
        # Check if API is running
        response = requests.get(f"{API_BASE_URL}/")
        print(f"\n✓ API is running at {API_BASE_URL}")
    except requests.exceptions.ConnectionError:
        print(f"\n✗ Error: API is not running at {API_BASE_URL}")
        print("  Please start the API server first:")
        print("    python api/server.py")
        return
    
    # Run tests
    tests = [
        ("Health Check", test_health_check),
        ("Model Info", test_model_info),
        ("Metrics", test_metrics),
        ("Simple Optimization", test_optimize_simple),
        ("Complex Optimization", test_optimize_complex),
    ]
    
    results = {}
    for name, test_func in tests:
        try:
            results[name] = test_func()
        except Exception as e:
            print(f"\n✗ Test failed: {e}")
            results[name] = False
    
    # Benchmark (optional)
    try:
        benchmark_api(num_requests=50)
    except Exception as e:
        print(f"\n✗ Benchmark failed: {e}")
    
    # Summary
    print("\n" + "="*70)
    print("  Test Summary")
    print("="*70)
    
    for name, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"  {status}: {name}")
    
    passed = sum(1 for p in results.values() if p)
    total = len(results)
    print(f"\n  Total: {passed}/{total} tests passed")
    
    print("\n" + "="*70 + "\n")


if __name__ == "__main__":
    main()
