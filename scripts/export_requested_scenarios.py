import json
import os
from pathlib import Path
from datetime import datetime

def export_to_rail(scenario_name, source_file):
    json_path = Path(f"scenarios/{source_file}")
    output_dir = Path("exports")
    output_dir.mkdir(exist_ok=True)
    output_path = output_dir / f"{scenario_name}.rail"
    
    if not json_path.exists():
        print(f"Error: {json_path} not found")
        return

    try:
        with open(json_path, 'r') as f:
            data = json.load(f)
            
        rail_data = {
            "stations": data.get("stations", []),
            "tracks": data.get("tracks", []),
            "metadata": {
                "exported_at": datetime.now().isoformat(),
                "original_scenario": scenario_name
            }
        }
        
        with open(output_path, 'w') as f:
            json.dump(rail_data, f, indent=2)
        print(f"Successfully exported {scenario_name} to {output_path}")
    except Exception as e:
        print(f"Failed to export {scenario_name}: {e}")

if __name__ == "__main__":
    tasks = [
        ("toscana", "toscana_cleaned.json"),
        ("roma", "roma.json"),
        ("london", "london.json")
    ]
    for name, file in tasks:
        export_to_rail(name, file)
