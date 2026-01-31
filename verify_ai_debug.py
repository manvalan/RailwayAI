import requests
import json
import time
import sys

# --- CONFIGURAZIONE ---
BASE_URL = "http://localhost:8002"  # Cambia in http://railway-ai.michelebigi.it:8080 se necessario
USERNAME = "admin"
PASSWORD = "admin"

def print_step(msg):
    print(f"\n[STEP] {msg}")
    print("-" * 50)

def verify_ai():
    print("="*60)
    print("🚀 RAILWAY AI - DIAGNOSTIC TEST SCRIPT")
    print("="*60)

    # 1. Test Health Check
    print_step("Verifica Health Check")
    try:
        resp = requests.get(f"{BASE_URL}/api/v1/health")
        print(f"Status Code: {resp.status_code}")
        print(f"Response: {resp.json()}")
        if resp.status_code != 200:
            print("❌ Health check fallito!")
    except Exception as e:
        print(f"❌ Errore di connessione: {e}")
        return

    # 2. Login per ottenere il Token
    print_step("Autenticazione (Ottengo Token)")
    token = None
    try:
        data = {"username": USERNAME, "password": PASSWORD}
        resp = requests.post(f"{BASE_URL}/token", data=data)
        print(f"Status Code: {resp.status_code}")
        if resp.status_code == 200:
            token = resp.json().get("access_token")
            print("✅ Token ottenuto con successo.")
        else:
            print(f"❌ Login fallito: {resp.text}")
            return
    except Exception as e:
        print(f"❌ Errore durante il login: {e}")
        return

    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    # 3. Verifica Info Modello
    print_step("Verifica Informazioni Modello AI")
    try:
        resp = requests.get(f"{BASE_URL}/api/v1/model/info", headers=headers)
        print(f"Status Code: {resp.status_code}")
        if resp.status_code == 200:
            info = resp.json()
            print(f"Architettura: {info.get('architecture')}")
            print(f"Parametri: {info.get('parameters')}")
            print(f"Stato: Caricato correttamente")
        else:
            print(f"❌ Impossibile ottenere info modello: {resp.text}")
    except Exception as e:
        print(f"❌ Errore info modello: {e}")

    # 4. Test Ottimizzazione (Inference)
    print_step("Test Ottimizzazione (Inference)")
    sample_request = {
        "trains": [
            {
                "id": 1,
                "position_km": 10.0,
                "velocity_kmh": 120.0,
                "current_track": 1,
                "destination_station": 5,
                "priority": 8
            },
            {
                "id": 2,
                "position_km": 15.0,
                "velocity_kmh": 100.0,
                "current_track": 1,
                "destination_station": 0,
                "priority": 5
            }
        ],
        "max_iterations": 10
    }
    
    try:
        start_time = time.time()
        resp = requests.post(
            f"{BASE_URL}/api/v1/optimize", 
            headers=headers, 
            data=json.dumps(sample_request)
        )
        duration = (time.time() - start_time) * 1000
        print(f"Status Code: {resp.status_code}")
        print(f"Tempo di esecuzione: {duration:.2f}ms")
        
        if resp.status_code == 200:
            result = resp.json()
            print("✅ AI Risponde correttamente!")
            print(f"Risoluzioni trovate: {len(result.get('resolutions', []))}")
            print(f"Ritardo Totale: {result.get('total_delay_minutes')} min")
        else:
            print(f"❌ Ottimizzazione fallita: {resp.text}")
    except Exception as e:
        print(f"❌ Errore durante l'ottimizzazione: {e}")

    print("\n" + "="*60)
    print("🏁 TEST COMPLETATO")
    print("="*60)

if __name__ == "__main__":
    if len(sys.argv) > 1:
        BASE_URL = sys.argv[1]
    verify_ai()
