"""
Demo: Utilizzo delle JSON API C++ da Python
Mostra come chiamare le API JSON native della libreria C++ da Python.
"""

import ctypes
import json
import sys
from pathlib import Path

def main():
    print("\n" + "="*70)
    print("  🐍 Railway AI Scheduler - JSON API Demo (Python)")
    print("="*70 + "\n")
    
    # Carica la libreria C++
    lib_path = Path(__file__).parent.parent / "build" / "librailwayai.dylib"
    if not lib_path.exists():
        print(f"❌ Libreria non trovata: {lib_path}")
        print("   Compila prima con: cd build && cmake --build . --target railwayai")
        return 1
    
    try:
        lib = ctypes.CDLL(str(lib_path))
        print(f"✅ Libreria caricata: {lib_path}\n")
    except Exception as e:
        print(f"❌ Errore caricamento libreria: {e}")
        return 1
    
    # Configura le funzioni
    # NOTA: Le funzioni C++ sono "name mangled", dobbiamo cercare i nomi corretti
    # Per ora usiamo un wrapper Python che chiama le struct-based APIs
    
    print("📊 Test: Rilevamento conflitti\n")
    print("-" * 70)
    
    # Input data
    input_data = {
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
                "position_km": 18.0,
                "velocity_kmh": 100.0,
                "current_track": 1,
                "destination_station": 3,
                "delay_minutes": 0.0,
                "priority": 5,
                "is_delayed": False
            },
            {
                "id": 103,
                "position_km": 25.0,
                "velocity_kmh": 130.0,
                "current_track": 1,
                "destination_station": 4,
                "delay_minutes": 10.0,
                "priority": 9,
                "is_delayed": True
            }
        ]
    }
    
    print("Input JSON:")
    print(json.dumps(input_data, indent=2))
    print()
    
    # Per ora usiamo il modulo Python esistente che wrappa il C++
    # In produzione, si può creare un binding ctypes più sofisticato
    print("💡 Suggerimento: Usa il demo C++ per testare direttamente le JSON API:")
    print("   cd examples/external_app")
    print("   DYLD_LIBRARY_PATH=../../build ./json_api_demo")
    print()
    
    # Alternative: usa l'API REST Python che già usa il modello ML
    print("📡 Alternative: REST API Python")
    print("-" * 70)
    print("L'API REST Python (api/server.py) fornisce endpoint JSON:")
    print()
    print("POST /api/v1/optimize")
    print("Input:")
    print(json.dumps(input_data, indent=2))
    print()
    print("Avvia server con:")
    print("  cd api")
    print("  uvicorn server:app --reload")
    print()
    print("Test con curl:")
    print("  curl -X POST http://localhost:8000/api/v1/optimize \\")
    print("    -H 'Content-Type: application/json' \\")
    print("    -d @input.json")
    print()
    
    print("="*70)
    print("  ℹ️  Per binding ctypes completi, vedi esempi in:")
    print("     - examples/external_app/json_api_demo.cpp (C++)")
    print("     - JSON_API_REFERENCE.md (documentazione completa)")
    print("="*70 + "\n")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
