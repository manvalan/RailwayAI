"""
Client di test per API FDC.

Dimostra l'uso dell'endpoint /api/v2/optimize.
"""

import requests
import json
from datetime import datetime


API_BASE = "http://localhost:8002"


def test_platform_conflict():
    """Test: Conflitto binario a MONZA."""
    print("\n" + "="*60)
    print("TEST 1: Conflitto binario a MONZA")
    print("="*60)
    
    request_data = {
        "conflicts": [
            {
                "conflict_type": "platform_conflict",
                "location": "MONZA",
                "trains": [
                    {
                        "train_id": "IC101",
                        "arrival": "2025-11-19T08:08:00",
                        "departure": "2025-11-19T08:10:00",
                        "platform": 1,
                        "priority": 8
                    },
                    {
                        "train_id": "R203",
                        "arrival": "2025-11-19T08:09:00",
                        "departure": "2025-11-19T08:11:00",
                        "platform": 1,
                        "priority": 5
                    }
                ],
                "severity": "high",
                "time_overlap_seconds": 60
            }
        ],
        "network": {
            "stations": ["MILANO_CENTRALE", "MONZA", "COMO"],
            "available_platforms": {
                "MONZA": [1, 2, 3]
            },
            "max_speeds": {
                "MILANO_MONZA": 140.0
            }
        }
    }
    
    print("\n📤 Request:")
    print(json.dumps(request_data, indent=2))
    
    response = requests.post(f"{API_BASE}/api/v2/optimize", json=request_data)
    
    print(f"\n📥 Response Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(json.dumps(data, indent=2))
        
        # Verifica risultati
        print("\n✅ VERIFICHE:")
        print(f"   Success: {data['success']}")
        print(f"   Total impact: {data['total_impact_minutes']} minutes")
        print(f"   Modifications: {len(data['modifications'])}")
        print(f"   Conflicts resolved: {data['conflict_analysis']['resolved_conflicts']}")
        
        if data['modifications']:
            mod = data['modifications'][0]
            print(f"\n   Modifica principale:")
            print(f"   - Train: {mod['train_id']}")
            print(f"   - Type: {mod['modification_type']}")
            
            if mod['modification_type'] == 'platform_change':
                params = mod['parameters']
                print(f"   - Platform change: {params['original_platform']} → {params['new_platform']}")
    else:
        print(f"❌ Error: {response.text}")


def test_timing_conflict():
    """Test: Conflitto temporale."""
    print("\n" + "="*60)
    print("TEST 2: Conflitto temporale con riduzione velocità")
    print("="*60)
    
    request_data = {
        "conflicts": [
            {
                "conflict_type": "timing_conflict",
                "location": "COMO",
                "trains": [
                    {
                        "train_id": "IC101",
                        "arrival": "2025-11-19T08:30:00",
                        "current_speed_kmh": 140.0,
                        "priority": 7
                    },
                    {
                        "train_id": "R205",
                        "arrival": "2025-11-19T08:31:00",
                        "current_speed_kmh": 100.0,
                        "priority": 5
                    }
                ],
                "severity": "medium",
                "time_overlap_seconds": 30
            }
        ],
        "network": {
            "stations": ["MONZA", "COMO"],
            "available_platforms": {
                "COMO": [1, 2]
            },
            "max_speeds": {
                "MONZA_COMO": 120.0
            }
        }
    }
    
    print("\n📤 Request:")
    print(json.dumps(request_data, indent=2))
    
    response = requests.post(f"{API_BASE}/api/v2/optimize", json=request_data)
    
    print(f"\n📥 Response Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(json.dumps(data, indent=2))
        
        print("\n✅ VERIFICHE:")
        print(f"   Success: {data['success']}")
        print(f"   Total impact: {data['total_impact_minutes']} minutes")
        
        if data['modifications']:
            mod = data['modifications'][0]
            print(f"\n   Modifica principale:")
            print(f"   - Train: {mod['train_id']}")
            print(f"   - Type: {mod['modification_type']}")
            
            if mod['modification_type'] == 'speed_reduction':
                params = mod['parameters']
                print(f"   - Speed: {params['original_speed_kmh']} → {params['new_speed_kmh']} km/h")
    else:
        print(f"❌ Error: {response.text}")


def test_simple_endpoint():
    """Test: Endpoint semplificato."""
    print("\n" + "="*60)
    print("TEST 3: Endpoint semplificato")
    print("="*60)
    
    request_data = {
        "train_id": "IC101",
        "origin_station": "MILANO_CENTRALE",
        "delay_seconds": 180,
        "affected_stations": ["MILANO_CENTRALE", "MONZA", "COMO"],
        "reason": "Ritardo per evitare conflitto",
        "confidence": 0.85
    }
    
    print("\n📤 Request:")
    print(json.dumps(request_data, indent=2))
    
    response = requests.post(f"{API_BASE}/api/v2/optimize/simple", json=request_data)
    
    print(f"\n📥 Response Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(json.dumps(data, indent=2))
        
        print("\n✅ VERIFICHE:")
        print(f"   Success: {data['success']}")
        print(f"   Total impact: {data['total_impact_minutes']} minutes")
    else:
        print(f"❌ Error: {response.text}")


def test_modification_types():
    """Test: Lista tipi modifiche."""
    print("\n" + "="*60)
    print("TEST 4: Lista tipi modifiche supportate")
    print("="*60)
    
    response = requests.get(f"{API_BASE}/api/v2/modification-types")
    
    if response.status_code == 200:
        data = response.json()
        print(json.dumps(data, indent=2))
        
        print(f"\n✅ Trovati {len(data['modification_types'])} tipi supportati")
    else:
        print(f"❌ Error: {response.text}")


def test_validate():
    """Test: Validazione modifiche."""
    print("\n" + "="*60)
    print("TEST 5: Validazione modifiche")
    print("="*60)
    
    # Modifica valida
    valid_mod = {
        "train_id": "IC101",
        "modification_type": "platform_change",
        "section": {
            "station": "MONZA"
        },
        "parameters": {
            "new_platform": 2,
            "original_platform": 1
        },
        "impact": {
            "time_increase_seconds": 0,
            "affected_stations": ["MONZA"],
            "passenger_impact_score": 0.1
        }
    }
    
    # Modifica non valida (campi mancanti)
    invalid_mod = {
        "train_id": "R203",
        "modification_type": "speed_reduction"
        # Mancano: section, parameters, impact
    }
    
    request_data = {
        "modifications": [valid_mod, invalid_mod]
    }
    
    print("\n📤 Request:")
    print(json.dumps(request_data, indent=2))
    
    response = requests.post(f"{API_BASE}/api/v2/validate", json=request_data)
    
    if response.status_code == 200:
        data = response.json()
        print(f"\n📥 Response:")
        print(json.dumps(data, indent=2))
        
        if data['valid']:
            print("\n✅ Tutte le modifiche sono valide")
        else:
            print(f"\n❌ Trovati {len(data['errors'])} errori di validazione")
    else:
        print(f"❌ Error: {response.text}")


def main():
    """Esegue tutti i test."""
    print("\n🚂 RailwayAI FDC Integration API - Test Client")
    print("="*60)
    
    # Verifica che API sia online
    try:
        response = requests.get(f"{API_BASE}/")
        if response.status_code == 200:
            info = response.json()
            print(f"✅ API online: {info['service']} v{info['version']}")
        else:
            print("❌ API non raggiungibile")
            return
    except Exception as e:
        print(f"❌ Errore connessione: {e}")
        print(f"   Assicurati che l'API sia in esecuzione su {API_BASE}")
        return
    
    # Esegui test
    test_platform_conflict()
    test_timing_conflict()
    test_simple_endpoint()
    test_modification_types()
    test_validate()
    
    print("\n" + "="*60)
    print("✅ Test completati!")
    print("="*60)


if __name__ == '__main__':
    main()
