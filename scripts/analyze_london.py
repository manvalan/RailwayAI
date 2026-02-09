import json
import networkx as nx

def analyze_london(file_path):
    with open(file_path, 'r') as f:
        data = json.load(f)
    
    G = nx.Graph()
    for track in data['tracks']:
        s1, s2 = track['station_ids']
        G.add_edge(s1, s2, weight=track['length_km'], id=track['id'])
    
    components = list(nx.connected_components(G))
    print(f"Total Stations in Graph: {G.number_of_nodes()}")
    print(f"Total Tracks in Graph: {G.number_of_edges()}")
    print(f"Number of Connected Components: {len(components)}")
    
    comp_sizes = [len(c) for c in components]
    comp_sizes.sort(reverse=True)
    print(f"Top 5 Component Sizes: {comp_sizes[:5]}")
    
    # Check if trains can reach their destinations
    reachable_count = 0
    for train in data['trains']:
        start_node = None
        # Find station for current track
        for track in data['tracks']:
            if track['id'] == train['current_track']:
                start_node = track['station_ids'][0]
                break
        
        dest_node = train['destination_station']
        if start_node is not None and dest_node in G:
            if nx.has_path(G, start_node, dest_node):
                reachable_count += 1
    
    print(f"Trains with reachable destinations: {reachable_count}/{len(data['trains'])}")

if __name__ == "__main__":
    analyze_london('scenarios/london.json')
