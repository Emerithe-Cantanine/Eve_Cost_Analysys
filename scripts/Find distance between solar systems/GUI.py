import sqlite3
import tkinter as tk
from tkinter import ttk, messagebox
from collections import deque

DB_PATH = "F:\Eve Cost Analysis\CostAnalysis.db"

def get_solar_systems(conn):
    cursor = conn.cursor()
    cursor.execute("SELECT solarSystemName FROM SolarSystems WHERE security > 0.5 ORDER BY solarSystemName")
    return [row[0] for row in cursor.fetchall()]

def get_system_id(conn, name):
    cursor = conn.cursor()
    cursor.execute("SELECT solarSystemID FROM SolarSystems WHERE solarSystemName = ?", (name,))
    result = cursor.fetchone()
    return result[0] if result else None

def build_graph(conn):
    cursor = conn.cursor()
    cursor.execute("SELECT solarSystemID FROM SolarSystems WHERE security > 0.45")
    valid = set(row[0] for row in cursor.fetchall())
    cursor.execute("SELECT fromSolarSystemID, toSolarSystemID FROM SolarSystemJumps")
    graph = {}
    for f, t in cursor.fetchall():
        if f in valid and t in valid:
            graph.setdefault(f, []).append(t)
            graph.setdefault(t, []).append(f)
    return graph

def bfs(graph, start, goal):
    queue = deque([(start, 0)])
    visited = set()
    while queue:
        current, depth = queue.popleft()
        if current == goal:
            return depth
        if current not in visited:
            visited.add(current)
            for neighbor in graph.get(current, []):
                if neighbor not in visited:
                    queue.append((neighbor, depth + 1))
    return None

def calculate_jumps(start_name, end_name):
    conn = sqlite3.connect(DB_PATH)
    try:
        start_id = get_system_id(conn, start_name)
        end_id = get_system_id(conn, end_name)
        if not start_id or not end_id:
            return None
        graph = build_graph(conn)
        return bfs(graph, start_id, end_id)
    finally:
        conn.close()

def on_calculate():
    start = start_var.get()
    end = end_var.get()
    if start == end:
        messagebox.showinfo("Result", "Start and destination systems are the same.")
        return
    result = calculate_jumps(start, end)
    if result is None:
        messagebox.showerror("Result", f"No path found between {start} and {end}.")
    else:
        messagebox.showinfo("Result", f"Jumps from {start} to {end}: {result}")

# GUI setup
root = tk.Tk()
root.title("Solar System Jump Calculator")

conn = sqlite3.connect(DB_PATH)
systems = get_solar_systems(conn)
conn.close()

start_var = tk.StringVar()
end_var = tk.StringVar()

ttk.Label(root, text="From:").grid(row=0, column=0, padx=5, pady=5)
ttk.Combobox(root, textvariable=start_var, values=systems).grid(row=0, column=1)

ttk.Label(root, text="To:").grid(row=1, column=0, padx=5, pady=5)
ttk.Combobox(root, textvariable=end_var, values=systems).grid(row=1, column=1)

ttk.Button(root, text="Calculate Jumps", command=on_calculate).grid(row=2, column=0, columnspan=2, pady=10)

root.mainloop()
