
import requests
import json
import os
import sys
import logging
import math

# Force INFO level logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Bounding box for Siena-Empoli-Firenze area
# [min_lat, min_lon, max_lat, max_lon]
BBOX = "43.25,10.85,43.85,11.45" 

OVERPASS_URL = "https://lz4.overpass-api.de/api/interpreter"

def fetch_siena_line():
    query = f"""
    [out:json][timeout:180];
    (
      way["railway"="rail"]({BBOX});
      node["railway"~"station|halt|stop_position"]({BBOX});
    );
    out body;
    >;
    out skel qt;
    """
    
    logger.info("Fetching real-world railway data for Siena-Empoli-Firenze via BBOX...")
    try:
        response = requests.post(OVERPASS_URL, data={'data': query}, timeout=190)
        response.raise_for_status()
        data = response.json()
        
        elements = data.get('elements', [])
        if not elements:
            logger.error("No elements found in this area.")
            return None
            
        logger.info(f"Success! Found {len(elements)} elements.")
        return data
    except Exception as e:
        logger.error(f"Failed to fetch data: {e}")
        return None

if __name__ == "__main__":
    result = fetch_siena_line()
    if result:
        # Re-use existing processing logic if possible, or just dump for inspection
        output_path = "scenarios/siena_empoli_real.json"
        # We need to import the processing function from the original script
        from fetch_osm_rail import process_to_scenario
        
        # Mock args
        class Args:
            num_trains = 15
            random_seed = 42
            output = output_path
            
        process_to_scenario(result, output_path, Args())
        logger.info(f"Scenario saved to {output_path}")
    else:
        sys.exit(1)
