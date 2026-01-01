import sqlite3
from functools import lru_cache
from contextlib import closing

# ---------------- Configuration ----------------
DB_PATH = "../../CostAnalysis.db"
MANUFACTURING_ACTIVITY_ID = 1  # used only if the table has an activityID column
BATCH_SIZE = 500               # commit after this many updates for speed
# ------------------------------------------------

def table_has_column(conn, table_name, column_name) -> bool:
    cur = conn.execute(f"PRAGMA table_info({table_name})")
    return any(row[1].lower() == column_name.lower() for row in cur.fetchall())

def fetch_all_craftable_items(conn):
    """
    Returns list of tuples: (typeID, blueprintID) for items where blueprintID is not null.
    """
    cur = conn.execute("""
        SELECT typeID, blueprintID
        FROM Items
        WHERE blueprintID IS NOT NULL
    """)
    return cur.fetchall()

def ensure_layer_column(conn):
    """
    Verifies that the Items table has a 'layer' column. If not, tries to add it.
    """
    if not table_has_column(conn, "Items", "layer"):
        conn.execute("ALTER TABLE Items ADD COLUMN layer INTEGER")

def build_schema_flags(conn):
    """
    Detect whether BlueprintActivityMaterialRequirements has activityID column.
    """
    has_activity_id = table_has_column(conn, "BlueprintActivityMaterialRequirements", "activityID")
    return {"has_activity_id": has_activity_id}

def get_materials_fetcher(conn, schema_flags):
    """
    Returns a function get_material_type_ids(blueprint_type_id) -> list[int]
    that pulls materialTypeIDs for a given blueprint typeID, optionally filtered by manufacturing activity.
    """
    if schema_flags["has_activity_id"]:
        sql = """
            SELECT materialTypeID
            FROM BlueprintActivityMaterialRequirements
            WHERE typeID = ? AND activityID = ?
        """
        def _fetch(blueprint_type_id: int):
            cur = conn.execute(sql, (blueprint_type_id, MANUFACTURING_ACTIVITY_ID))
            return [row[0] for row in cur.fetchall()]
    else:
        sql = """
            SELECT materialTypeID
            FROM BlueprintActivityMaterialRequirements
            WHERE typeID = ?
        """
        def _fetch(blueprint_type_id: int):
            cur = conn.execute(sql, (blueprint_type_id,))
            return [row[0] for row in cur.fetchall()]
    return _fetch

def get_blueprint_lookup(conn):
    """
    Returns a function blueprint_id_for_product(product_type_id) -> int|None
    Looks up the blueprintID for a given *product* typeID from Items.
    """
    sql = "SELECT blueprintID FROM Items WHERE typeID = ?"
    def _lookup(product_type_id: int):
        cur = conn.execute(sql, (product_type_id,))
        row = cur.fetchone()
        return row[0] if row and row[0] is not None else None
    return _lookup

def compute_layers_for_all(conn):
    """
    Computes and writes the layer depth for all items with a blueprintID.
    """
    ensure_layer_column(conn)
    schema_flags = build_schema_flags(conn)
    get_material_type_ids = get_materials_fetcher(conn, schema_flags)
    blueprint_id_for_product = get_blueprint_lookup(conn)

    # Memoize depth by blueprint typeID to avoid recomputation
    @lru_cache(maxsize=None)
    def depth_from_blueprint(blueprint_type_id: int) -> int:
        """
        Returns the number of sub-component layers for a given blueprint typeID.
        Immediate materials = depth 1. If materials have craftable subparts, depth increases.
        If no materials found, returns 0.
        """
        # DFS with cycle protection per call chain
        visited_stack = set()
        def dfs(bp_id: int) -> int:
            if bp_id in visited_stack:
                # Cycle detected; treat as no further depth to avoid infinite loops.
                return 0
            visited_stack.add(bp_id)

            materials = get_material_type_ids(bp_id)
            if not materials:
                visited_stack.remove(bp_id)
                return 0  # no sub-components listed

            max_child = 0
            for mat_type in materials:
                child_bp = blueprint_id_for_product(mat_type)
                if child_bp:
                    # Recurse into cached entry (but preserve per-branch cycle protection)
                    # We can't pass visited_stack through cache, so call a helper without cache here:
                    max_child = max(max_child, _depth_from_blueprint_no_cache(child_bp, visited_stack))
                else:
                    # Raw material contributes no additional layers beneath it
                    max_child = max(max_child, 0)

            visited_stack.remove(bp_id)
            # Immediate materials = 1 layer, plus the max depth beneath them
            return 1 + max_child

        # local helper (no cache) to keep cycle detection intact across branches
        def _depth_from_blueprint_no_cache(bp_id: int, stack: set) -> int:
            if bp_id in stack:
                return 0
            stack.add(bp_id)
            mats = get_material_type_ids(bp_id)
            if not mats:
                stack.remove(bp_id)
                return 0
            child_max = 0
            for m in mats:
                child_bp = blueprint_id_for_product(m)
                if child_bp:
                    child_max = max(child_max, _depth_from_blueprint_no_cache(child_bp, stack))
                else:
                    child_max = max(child_max, 0)
            stack.remove(bp_id)
            return 1 + child_max

        # Use cached dfs result
        return dfs(blueprint_type_id)

    # Process all craftable items
    items = fetch_all_craftable_items(conn)
    print(f"Found {len(items)} craftable items.")

    updates = []
    for idx, (product_type_id, blueprint_type_id) in enumerate(items, start=1):
        try:
            depth = depth_from_blueprint(int(blueprint_type_id))
        except Exception as e:
            print(f"Error computing depth for product typeID {product_type_id} (bp {blueprint_type_id}): {e}")
            depth = None

        if depth is not None:
            updates.append((depth, product_type_id))

        # Batch commit
        if len(updates) >= BATCH_SIZE:
            conn.executemany("UPDATE Items SET layer = ? WHERE typeID = ?", updates)
            conn.commit()
            print(f"Updated {idx} / {len(items)} items...")
            updates.clear()

    if updates:
        conn.executemany("UPDATE Items SET layer = ? WHERE typeID = ?", updates)
        conn.commit()

    print("Done.")

def main():
    with closing(sqlite3.connect(DB_PATH)) as conn:
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA synchronous = NORMAL")
        compute_layers_for_all(conn)

if __name__ == "__main__":
    main()
