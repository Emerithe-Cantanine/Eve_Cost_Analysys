import sqlite3
from collections import deque

def build_graph(conn, sec_status):
    cursor = conn.cursor()
    
    # Get all valid solar systems with security > sec_status
    cursor.execute(f"SELECT solarSystemID FROM SolarSystems WHERE security > {sec_status}")
    valid_systems = set(row[0] for row in cursor.fetchall())
    
    # Build graph from SolarSystemJumps
    graph = {}
    cursor.execute("SELECT fromSolarSystemID, toSolarSystemID FROM SolarSystemJumps")
    
    for from_id, to_id in cursor.fetchall():
        if from_id in valid_systems and to_id in valid_systems:
            graph.setdefault(from_id, []).append(to_id)
            graph.setdefault(to_id, []).append(from_id)  # Bidirectional

    return graph

def bfs_shortest_path(graph, start_id, end_id):
    visited = set()
    queue = deque([(start_id, 0)])  # (current_node, depth)

    while queue:
        current, depth = queue.popleft()
        if current == end_id:
            return depth
        if current not in visited:
            visited.add(current)
            for neighbor in graph.get(current, []):
                if neighbor not in visited:
                    queue.append((neighbor, depth + 1))
    return None  # No path found

def find_jumps_between_system_ids(db_path, start_id, end_id, sec_status):
    conn = sqlite3.connect(db_path)
    try:
        graph = build_graph(conn, sec_status)
        jumps = bfs_shortest_path(graph, start_id, end_id)
        
        if jumps is not None:
            return jumps
            print(f"Number of jumps from {start_id} to {end_id}: {jumps}")
        else:
            return None
            print(f"No valid path found from {start_id} to {end_id}.")
    finally:
        conn.close()

# Example usage
# Replace with actual IDs you want to test
find_jumps_between_system_ids(r"../../CostAnalysis.db", 30003909, 30005003, -2.0)
