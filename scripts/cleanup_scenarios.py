import json
import os
from pathlib import Path

def validate_scenario(path):
    try:
        with open(path, 'r') as f:
            data = json.load(f)
            # Basic validation
            if not isinstance(data, dict):
                return False, "Not a dictionary"
            
            # Check for mandatory keys
            # Support both English and Italian keys since I just added synonym support
            stations = data.get('stations') or data.get('stazioni') or data.get('nodi')
            tracks = data.get('tracks') or data.get('binari') or data.get('linee')
            
            if stations is None or tracks is None:
                return False, f"Missing stations or tracks. Keys: {list(data.keys())}"
            
            if not isinstance(stations, list) or not isinstance(tracks, list):
                return False, "stations or tracks is not a list"
                
            return True, "Valid"
    except Exception as e:
        return False, str(e)

scenarios_dir = Path("scenarios")
for p in scenarios_dir.glob("*.json"):
    is_valid, reason = validate_scenario(p)
    if not is_valid:
        print(f"Deleting invalid scenario: {p.name} - Reason: {reason}")
        os.remove(p)
    else:
        print(f"Scenario valid: {p.name}")
