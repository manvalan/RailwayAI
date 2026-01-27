import json
import os
import networkx as nx
import logging

logger = logging.getLogger(__name__)

class ScenarioLoader:
    """
    Utility to load and validate railway scenarios from JSON files.
    """
    
    @staticmethod
    def load_scenario(file_path: str) -> dict:
        """Loads a scenario and performs basic validation."""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Scenario file not found: {file_path}")
            
        with open(file_path, 'r') as f:
            data = json.load(f)
            
        # Validation
        if 'tracks' not in data or 'stations' not in data or 'trains' not in data:
            raise ValueError("Scenario must contain 'tracks', 'stations', and 'trains'")
            
        # Inject default routes if missing
        ScenarioLoader._inject_default_routes(data)
        
        return data

    @staticmethod
    def _inject_default_routes(data: dict):
        """Calculate default routes if trains don't have a planned_route."""
        graph = nx.Graph()
        valid_tracks = 0
        for t in data['tracks']:
            if len(t.get('station_ids', [])) >= 2:
                graph.add_edge(t['station_ids'][0], t['station_ids'][1], id=t['id'])
                valid_tracks += 1
            else:
                logger.warning(f"Skipping track {t.get('id')} due to insufficient stations: {t.get('station_ids')}")
        
        if valid_tracks == 0:
            logger.error("No valid tracks found in scenario topology!")
            return

        for train in data['trains']:
            if 'planned_route' not in train or not train['planned_route']:
                # Find current station based on current_track or assume start at origin
                try:
                    curr_track_id = train['current_track']
                    curr_track = next((t for t in data['tracks'] if t['id'] == curr_track_id), None)
                    
                    if not curr_track or len(curr_track.get('station_ids', [])) < 1:
                        continue
                        
                    start_node = curr_track['station_ids'][0]
                    end_node = train['destination_station']
                    
                    if start_node == end_node:
                        train['planned_route'] = [curr_track_id]
                        continue
                        
                    # Use BFS to find shortest path in station graph
                    path_nodes = nx.shortest_path(graph, start_node, end_node)
                    
                    # Convert node path to track path
                    route = []
                    for i in range(len(path_nodes)-1):
                        edge_data = graph.get_edge_data(path_nodes[i], path_nodes[i+1])
                        route.append(edge_data['id'])
                    
                    train['planned_route'] = route
                except (nx.NetworkXNoPath, StopIteration, KeyError) as e:
                    logger.warning(f"Could not calculate route for train {train['id']}: {e}")
                    train['planned_route'] = [train['current_track']]
