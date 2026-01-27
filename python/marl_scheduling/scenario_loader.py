import json
import logging
from typing import Dict, List, Any
import networkx as nx

logger = logging.getLogger(__name__)

class ScenarioLoader:
    """Loads railway infrastructure and train data from JSON files."""
    
    @staticmethod
    def load_scenario(file_path: str) -> Dict[str, Any]:
        with open(file_path, 'r') as f:
            data = json.load(f)
            
        # Basic validation
        required = ['tracks', 'stations', 'trains']
        for key in required:
            if key not in data:
                raise ValueError(f"Missing required key '{key}' in scenario file.")
                
        # Inject routes if missing (using shortest path as default)
        ScenarioLoader._inject_default_routes(data)
        
        return data

    @staticmethod
    def _inject_default_routes(data: Dict[str, Any]):
        """Calculate default routes if trains don't have a planned_route."""
        graph = nx.Graph()
        for t in data['tracks']:
            graph.add_edge(t['station_ids'][0], t['station_ids'][1], id=t['id'])
            
        for train in data['trains']:
            if 'planned_route' not in train or not train['planned_route']:
                # Find current station based on current_track or assume start at origin
                # This is simplified: in actual_problem_scenario, trains start at a track id.
                # Here we assume we can reach destination_station from current_track.
                
                # Logic to find path of track IDs
                # This requires more complex graph handling to return edges, not nodes.
                pass
            
            # Ensure all numeric fields are present
            train.setdefault('velocity_kmh', 120.0)
            train.setdefault('priority', 5)
            train.setdefault('delay_min', 0.0)
            train.setdefault('route_index', 0)
            train.setdefault('position_on_track', 0.0)
