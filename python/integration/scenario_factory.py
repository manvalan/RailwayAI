import os
import sys
import json
import asyncio
import logging
import time
from pathlib import Path

logger = logging.getLogger(__name__)

class ScenarioFactory:
    """
    Handles the end-to-end creation of AI-ready scenarios.
    Download -> Refinement -> Traffic Injection -> Registration
    """
    
    def __init__(self, scenarios_dir="scenarios", script_path="scripts/fetch_osm_rail.py"):
        self.scenarios_dir = Path(scenarios_dir)
        self.scenarios_dir.mkdir(exist_ok=True)
        self.script_path = script_path
        
    async def provision_region(self, region_name):
        """
        Main entry point: fetches data and prepares it for the AI.
        """
        slug = region_name.lower().replace(" ", "_")
        output_file = self.scenarios_dir / f"{slug}_factory.json"
        
        logger.info(f"Provisioning region: {region_name} -> {output_file}")
        
        # 1. Download and convert from OSM
        success = await self._download_region(region_name, output_file)
        if not success:
            return None
            
        # 2. Refine and Inject Traffic
        scenario = self._inject_ai_traffic(output_file)
        
        return {
            "name": region_name,
            "slug": slug,
            "path": str(output_file),
            "stations": len(scenario.get("stations", [])),
            "tracks": len(scenario.get("tracks", [])),
            "trains": len(scenario.get("trains", []))
        }

    async def _download_region(self, region_name, output_path):
        """Runs the external fetcher script."""
        import sys
        cmd = [
            sys.executable,
            self.script_path,
            "--area", region_name,
            "--output", str(output_path)
        ]
        
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        
        if process.returncode == 0 and output_path.exists():
            logger.info(f"Download successful for {region_name}")
            return True
        else:
            err = stderr.decode() if stderr else "Unknown error"
            logger.error(f"Download failed for {region_name}: {err}")
            return False

    def _inject_ai_traffic(self, scenario_path):
        """
        Adds synthetic trains to a downloaded scenario to make it ready for training.
        """
        with open(scenario_path, 'r') as f:
            data = json.load(f)
            
        stations = data.get("stations", [])
        tracks = data.get("tracks", [])
        
        if not stations or not tracks:
            logger.warning("Scenario has no stations or tracks, cannot inject traffic.")
            return data
            
        # Clear existing trains if any
        data["trains"] = []
        
        # Heuristic: num trains based on network complexity
        num_trains = min(20, max(5, len(tracks) // 5))
        
        import random
        track_ids = [t["id"] for t in tracks]
        station_ids = [s["id"] for s in stations]
        
        for i in range(num_trains):
            # Create a set of 3 unique destination stations to form a route
            destinations = random.sample(station_ids, min(3, len(station_ids)))
            
            data["trains"].append({
                "id": i,
                "current_track": random.choice(track_ids),
                "position_km": 0.0,
                "destination_station": destinations[-1], # Final destination
                "planned_route": destinations, # List of stations to visit
                "priority": random.randint(1, 10),
                "velocity_kmh": random.choice([100, 120, 160, 200]),
                "status": "active"
            })
            
        with open(scenario_path, 'w') as f:
            json.dump(data, f, indent=2)
            
        logger.info(f"Injected {len(data['trains'])} trains into {scenario_path}")
        return data

# Singleton instance
factory = ScenarioFactory()
