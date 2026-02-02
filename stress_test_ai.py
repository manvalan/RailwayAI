import requests
import json
import time
import random
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

def run_stress_test():
    token = get_token()
    if not token:
        print("Impossibile ottenere il token. Verifica le credenziali.")
        return

    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    
    print("="*60)
    print("🚦 RAILWAY AI - STRESS & DYNAMIC MONITORING TEST")
    print("="*60)
    print("Questo test invierà scenari variabili ogni 3 secondi per testare la Dashboard.")

    try:
        for i in range(10):
            num_trains = random.randint(2, 15)
            # Metà dei treni saranno "in ritardo" per simulare conflitti
            trains = []
            conflicts_simulated = 0
            
            for t_id in range(num_trains):
                is_delayed = random.choice([True, False])
                if is_delayed: conflicts_simulated += 1
                
                trains.append({
                    "id": t_id + 1,
                    "position_km": round(random.uniform(0, 50), 1),
                    "velocity_kmh": round(random.uniform(80, 200), 1),
                    "current_track": random.randint(1, 10),
                    "destination_station": random.randint(1, 10),
                    "priority": random.randint(1, 10),
                    "is_delayed": is_delayed,
                    "delay_minutes": round(random.uniform(0, 30), 1) if is_delayed else 0.0
                })

            payload = {
                "trains": trains,
                "max_iterations": 20
            }

            start = time.time()
            resp = requests.post(f"{BASE_URL}/api/v1/optimize", headers=headers, data=json.dumps(payload))
            duration = (time.time() - start) * 1000
            
            if resp.status_code == 200:
                res = resp.json()
                print(f"[{i+1}/10] Invio {num_trains} treni ({conflicts_simulated} conflitti) -> AI OK ({duration:.1f}ms)")
            else:
                print(f"[{i+1}/10] Errore: {resp.status_code} - {resp.text}")
            
            time.sleep(3)

    except KeyboardInterrupt:
        print("\nTest interrotto dall'utente.")

    print("\n" + "="*60)
    print("🏁 STRESS TEST COMPLETATO")
    print("="*60)

if __name__ == "__main__":
    if len(sys.argv) > 1:
        BASE_URL = sys.argv[1]
    run_stress_test()
