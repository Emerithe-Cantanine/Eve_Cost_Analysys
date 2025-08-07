import sqlite3
from collections import deque

def get_solar_system_id_by_name(conn, name):
    cursor = conn.cursor()
    cursor.execute("SELECT solarSystemID FROM SolarSystems WHERE solarSystemName = ?", (name,))
    result = cursor.fetchone()
    return result[0] if result else None

def build_graph(conn):
    cursor = conn.cursor()
    
    # First, get all solar systems with security > 0.5
    cursor.execute("SELECT solarSystemID FROM SolarSystems WHERE security > 0.45")
    valid_systems = set(row[0] for row in cursor.fetchall())
    
    # Now build the graph
    graph = {}
    cursor.execute("SELECT fromSolarSystemID, toSolarSystemID FROM SolarSystemJumps")
    
    for from_id, to_id in cursor.fetchall():
        if from_id in valid_systems and to_id in valid_systems:
            graph.setdefault(from_id, []).append(to_id)
            graph.setdefault(to_id, []).append(from_id)  # Bidirectional travel
            
    return graph

def bfs_shortest_path(graph, start, goal):
    visited = set()
    queue = deque([(start, 0)])  # (current_node, jump_count)
    
    while queue:
        current, depth = queue.popleft()
        if current == goal:
            return depth
        if current not in visited:
            visited.add(current)
            for neighbor in graph.get(current, []):
                if neighbor not in visited:
                    queue.append((neighbor, depth + 1))
    return None  # No path found

def find_jumps_between_systems(db_path, start_name, end_name):
    conn = sqlite3.connect(db_path)
    try:
        start_id = get_solar_system_id_by_name(conn, start_name)
        end_id = get_solar_system_id_by_name(conn, end_name)
        
        if not start_id or not end_id:
            print(f"One or both system names are invalid: '{start_name}', '{end_name}'")
            return
        
        graph = build_graph(conn)
        jumps = bfs_shortest_path(graph, start_id, end_id)
        
        if jumps is not None:
            return f"Number of jumps from {start_name} to {end_name}: {jumps}"
        else:
            return f"No valid path found from {start_name} to {end_name}."
    finally:
        conn.close()

# Example usage
find_jumps_between_systems(r"F:\Eve Cost Analysis\CostAnalysis.db", "Zemalu", "Amarr")
