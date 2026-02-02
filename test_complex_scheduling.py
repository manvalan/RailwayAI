import requests
import json
import time
import sys

# --- CONFIGURAZIONE ---
BASE_URL = "http://localhost:8002"  # Cambia se necessario
USERNAME = "test"
PASSWORD = "test1234"

def get_token():
    try:
        data = {"username": USERNAME, "password": PASSWORD}
        resp = requests.post(f"{BASE_URL}/token", data=data)
        if resp.status_code == 200:
            return resp.json().get("access_token")
    except Exception as e:
        print(f"Errore Login: {e}")
    return None

def test_complex_scheduling():
    token = get_token()
    if not token:
        print("Impossibile ottenere il token.")
        return

    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    
    print("="*60)
    print("🧠 RAILWAY AI - COMPLEX SCHEDULER TEST (Route Planning)")
    print("="*60)

    # Scenario: Due treni che devono percorrere la stessa tratta da direzioni opposte
    payload = {
        "trains": [
            {
                "id": 101,
                "origin_station": 1,
                "destination_station": 5,
                "scheduled_departure_time": "09:00:00",
                "velocity_kmh": 150.0,
                "priority": 9,
                "position_km": 0.0,
                "current_track": 1
            },
            {
                "id": 202,
                "origin_station": 5,
                "destination_station": 1,
                "scheduled_departure_time": "09:02:00",
                "velocity_kmh": 120.0,
                "priority": 5,
                "position_km": 0.0,
                "current_track": 5
            }
        ],
        "tracks": [
            {"id": 1, "length_km": 10.0, "is_single_track": False, "capacity": 2, "station_ids": [1, 2]},
            {"id": 2, "length_km": 20.0, "is_single_track": True, "capacity": 1, "station_ids": [2, 3]}, # COLLO DI BOTTIGLIA
            {"id": 3, "length_km": 10.0, "is_single_track": False, "capacity": 2, "station_ids": [3, 4]},
            {"id": 4, "length_km": 10.0, "is_single_track": False, "capacity": 2, "station_ids": [4, 5]},
            {"id": 5, "length_km": 5.0, "is_single_track": False, "capacity": 5, "station_ids": [5]}
        ],
        "stations": [
            {"id": 1, "name": "Milano", "num_platforms": 10},
            {"id": 2, "name": "Monza", "num_platforms": 4},
            {"id": 3, "name": "Carnate", "num_platforms": 3},
            {"id": 4, "name": "Cernusco", "num_platforms": 2},
            {"id": 5, "name": "Lecco", "num_platforms": 5}
        ],
        "max_iterations": 60 # Simula i prossimi 60 minuti
    }

    try:
        print(f"Invio scenario complesso (1 binario unico tra Monza e Carnate)...")
        start_time = time.time()
        # Nota: utilizzo l'endpoint /api/v1/optimize_scheduled
        resp = requests.post(f"{BASE_URL}/api/v1/optimize_scheduled", headers=headers, data=json.dumps(payload))
        duration = (time.time() - start_time) * 1000
        
        print(f"Status Code: {resp.status_code}")
        print(f"Tempo di calcolo: {duration:.2f}ms")
        
        if resp.status_code == 200:
            result = resp.json()
            print("\n✅ AI ha analizzato lo scenario e calcolato i conflitti futuri:")
            print(f"Conflitti rilevati: {result.get('conflicts_detected')}")
            print(f"Risoluzioni proposte: {len(result.get('resolutions', []))}")
            
            for res in result.get('resolutions', []):
                print(f"  • Treno {res['train_id']}: aggiustamento tempo {res['time_adjustment_min']} min (Confidenza: {res['confidence']})")
                if res.get('dwell_delays'):
                    print(f"    Soste previste: {res['dwell_delays']}")
        else:
            print(f"❌ Errore: {resp.text}")

    except Exception as e:
        print(f"❌ Errore durante il test: {e}")

    print("\n" + "="*60)
    print("🏁 COMPLEX TEST COMPLETATO")
    print("="*60)

if __name__ == "__main__":
    if len(sys.argv) > 1:
        BASE_URL = sys.argv[1]
    test_complex_scheduling()
