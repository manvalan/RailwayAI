"""
Client di test per API Ottimizzatore Treni Opposti.

Esempi di utilizzo dell'API JSON.
"""

import requests
import json
from datetime import datetime, timedelta


API_BASE_URL = "http://localhost:8001"


def example_simple_line():
    """
    Esempio 1: Linea semplice con una sezione singolo binario 
    e una stazione di incrocio centrale.
    """
    print("\n" + "="*70)
    print("📝 ESEMPIO 1: Linea Semplice con Incrocio Centrale")
    print("="*70)
    
    request_data = {
        "track_sections": [
            # Stazione A (partenza)
            {
                "section_id": 1,
                "start_km": 0.0,
                "end_km": 2.0,
                "num_tracks": 2,
                "max_speed_kmh": 80.0,
                "has_station": True,
                "station_name": "Stazione A",
                "can_cross": True
            },
            # Singolo binario
            {
                "section_id": 2,
                "start_km": 2.0,
                "end_km": 18.0,
                "num_tracks": 1,
                "max_speed_kmh": 120.0,
                "has_station": False,
                "can_cross": False
            },
            # Stazione centrale (punto incrocio)
            {
                "section_id": 3,
                "start_km": 18.0,
                "end_km": 22.0,
                "num_tracks": 2,
                "max_speed_kmh": 80.0,
                "has_station": True,
                "station_name": "Stazione Centrale",
                "can_cross": True
            },
            # Singolo binario
            {
                "section_id": 4,
                "start_km": 22.0,
                "end_km": 38.0,
                "num_tracks": 1,
                "max_speed_kmh": 120.0,
                "has_station": False,
                "can_cross": False
            },
            # Stazione B (arrivo)
            {
                "section_id": 5,
                "start_km": 38.0,
                "end_km": 40.0,
                "num_tracks": 2,
                "max_speed_kmh": 80.0,
                "has_station": True,
                "station_name": "Stazione B",
                "can_cross": True
            }
        ],
        "train1": {
            "train_id": "R 1234",
            "direction": "forward",
            "start_km": 0.0,
            "end_km": 40.0,
            "avg_speed_kmh": 90.0,
            "stops": [[20.0, 3]],  # Fermata 3 min a Stazione Centrale
            "priority": 6
        },
        "train2": {
            "train_id": "R 5678",
            "direction": "backward",
            "start_km": 40.0,
            "end_km": 0.0,
            "avg_speed_kmh": 90.0,
            "stops": [[20.0, 3]],  # Fermata 3 min a Stazione Centrale
            "priority": 6
        },
        "time_window_start": "2025-11-19T08:00:00",
        "time_window_end": "2025-11-19T10:00:00",
        "frequency_minutes": 30  # Ogni 30 minuti
    }
    
    print("\n📤 Invio richiesta all'API...")
    print(f"   Linea: {request_data['track_sections'][0]['station_name']} → "
          f"{request_data['track_sections'][-1]['station_name']}")
    print(f"   Lunghezza totale: 40 km")
    print(f"   Sezioni singolo binario: 2 (totale 32 km)")
    
    response = requests.post(
        f"{API_BASE_URL}/api/v1/optimize-opposite-trains",
        json=request_data,
        headers={"Content-Type": "application/json"}
    )
    
    if response.status_code == 200:
        result = response.json()
        print(f"\n✅ Risposta ricevuta (computation time: {result['computation_time_ms']:.2f} ms)")
        print(f"   Proposte trovate: {len(result['proposals'])}")
        
        if result['best_proposal']:
            best = result['best_proposal']
            print(f"\n🏆 MIGLIORE PROPOSTA:")
            print(f"   {request_data['train1']['train_id']}: partenza {best['train1_departure']}")
            print(f"   {request_data['train2']['train_id']}: partenza {best['train2_departure']}")
            print(f"   Incrocio: km {best['crossing_point_km']:.1f} alle {best['crossing_time']}")
            print(f"   Attese: {best['train1_wait_minutes']:.0f} + {best['train2_wait_minutes']:.0f} "
                  f"= {best['total_delay_minutes']:.0f} min")
            print(f"   Confidence: {best['confidence']:.2f}")
            print(f"   {best['reasoning']}")
        
        # Mostra altre proposte
        if len(result['proposals']) > 1:
            print(f"\n📋 Altre {min(3, len(result['proposals'])-1)} proposte:")
            for i, p in enumerate(result['proposals'][1:4], 2):
                print(f"   {i}. Ritardo {p['total_delay_minutes']:.0f} min, "
                      f"confidence {p['confidence']:.2f}")
    else:
        print(f"❌ Errore: {response.status_code}")
        print(response.text)


def example_complex_network():
    """
    Esempio 2: Rete complessa con multiple sezioni singolo binario
    e varie stazioni di incrocio.
    """
    print("\n" + "="*70)
    print("📝 ESEMPIO 2: Rete Complessa Multi-Sezione")
    print("="*70)
    
    # Definisci rete più complessa
    sections = []
    km = 0.0
    
    # Pattern: doppio 5km, singolo 15km, doppio 5km (stazione), ripeti
    for i in range(4):
        # Doppio binario iniziale
        sections.append({
            "section_id": len(sections) + 1,
            "start_km": km,
            "end_km": km + 5.0,
            "num_tracks": 2,
            "max_speed_kmh": 100.0,
            "has_station": i == 0 or i == 3,
            "station_name": f"Stazione {chr(65+i)}" if i == 0 or i == 3 else None,
            "can_cross": True
        })
        km += 5.0
        
        # Singolo binario
        sections.append({
            "section_id": len(sections) + 1,
            "start_km": km,
            "end_km": km + 15.0,
            "num_tracks": 1,
            "max_speed_kmh": 120.0,
            "has_station": False,
            "can_cross": False
        })
        km += 15.0
        
        # Doppio binario con stazione
        if i < 3:  # Non dopo l'ultima
            sections.append({
                "section_id": len(sections) + 1,
                "start_km": km,
                "end_km": km + 5.0,
                "num_tracks": 2,
                "max_speed_kmh": 80.0,
                "has_station": True,
                "station_name": f"Stazione {chr(66+i)}",
                "can_cross": True
            })
            km += 5.0
    
    request_data = {
        "track_sections": sections,
        "train1": {
            "train_id": "IC 101",
            "direction": "forward",
            "start_km": 0.0,
            "end_km": km,
            "avg_speed_kmh": 100.0,
            "stops": [[30.0, 2], [55.0, 2]],  # Fermate intermedie
            "priority": 8
        },
        "train2": {
            "train_id": "IC 102",
            "direction": "backward",
            "start_km": km,
            "end_km": 0.0,
            "avg_speed_kmh": 100.0,
            "stops": [[55.0, 2], [30.0, 2]],  # Fermate intermedie
            "priority": 8
        },
        "time_window_start": "2025-11-19T14:00:00",
        "time_window_end": "2025-11-19T16:00:00",
        "frequency_minutes": 60,
        "existing_traffic": [
            # Aggiungi treno esistente per realismo
            {
                "train_id": "Merci 999",
                "position_km": 35.0,
                "velocity_kmh": 60.0,
                "direction": "forward"
            }
        ]
    }
    
    print(f"\n📤 Invio richiesta rete complessa...")
    print(f"   Lunghezza totale: {km:.0f} km")
    print(f"   Sezioni totali: {len(sections)}")
    print(f"   Sezioni singolo binario: {sum(1 for s in sections if s['num_tracks'] == 1)}")
    print(f"   Stazioni incrocio: {sum(1 for s in sections if s.get('can_cross', False))}")
    print(f"   Traffico esistente: {len(request_data['existing_traffic'])} treni")
    
    response = requests.post(
        f"{API_BASE_URL}/api/v1/optimize-opposite-trains",
        json=request_data,
        headers={"Content-Type": "application/json"}
    )
    
    if response.status_code == 200:
        result = response.json()
        print(f"\n✅ Risposta ricevuta (computation time: {result['computation_time_ms']:.2f} ms)")
        
        if result['best_proposal']:
            best = result['best_proposal']
            print(f"\n🏆 MIGLIORE SOLUZIONE:")
            print(f"   {request_data['train1']['train_id']}: {best['train1_departure']}")
            print(f"   {request_data['train2']['train_id']}: {best['train2_departure']}")
            print(f"   Incrocio: km {best['crossing_point_km']:.1f}")
            print(f"   Ritardo totale: {best['total_delay_minutes']:.0f} minuti")
            print(f"   Conflitti evitati: {best['conflicts_avoided']}")
            print(f"   {best['reasoning']}")
    else:
        print(f"❌ Errore: {response.status_code}")
        print(response.text)


def health_check():
    """Verifica che API sia attiva."""
    try:
        response = requests.get(f"{API_BASE_URL}/api/v1/health")
        if response.status_code == 200:
            return True
    except:
        return False
    return False


def main():
    """Esegui tutti gli esempi."""
    print("\n🚂 CLIENT TEST API OTTIMIZZATORE TRENI OPPOSTI")
    print("="*70)
    
    # Health check
    print("\n🔍 Verifico disponibilità API...")
    if not health_check():
        print("❌ API non raggiungibile!")
        print("   Avvia server con: python api/opposite_train_api.py")
        return
    
    print("✅ API attiva e funzionante")
    
    # Esegui esempi
    try:
        example_simple_line()
        example_complex_network()
        
        print("\n" + "="*70)
        print("✅ TEST COMPLETATI CON SUCCESSO")
        print("="*70)
        print("\n💡 TIP: Visualizza documentazione completa su:")
        print(f"   {API_BASE_URL}/docs")
        
    except Exception as e:
        print(f"\n❌ Errore durante test: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
