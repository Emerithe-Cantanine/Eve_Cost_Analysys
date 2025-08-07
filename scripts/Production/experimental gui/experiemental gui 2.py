import sqlite3
from collections import defaultdict
import tkinter as tk
from tkinter import ttk, messagebox

class CostCalculator:
    def __init__(self, db_path='F:\Eve Cost Analysis\CostAnalysis.db'):
        self.conn = sqlite3.connect(db_path)
        self.cursor = self.conn.cursor()
        self.used_materials = defaultdict(int)
        self.component_cost_cache = {}
        self.selected_region = None
        self.selected_system = None

    def get_market_price(self, typeID, quantity):
        query = """
            SELECT price FROM MarketOrdersAll
            WHERE typeID = ? AND buy_true_sell_false = 0
        """
        params = [typeID]

        if self.selected_system:
            query += " AND solarSystemID = ?"
            params.append(self.selected_system)
        elif self.selected_region:
            query += " AND regionID = ?"
            params.append(self.selected_region)

        query += " ORDER BY price ASC, dateIssued DESC LIMIT 1"
        self.cursor.execute(query, tuple(params))

        row = self.cursor.fetchone()
        return row[0] * quantity if row else float('inf')

    def get_blueprint_components(self, typeID):
        self.cursor.execute("""
            SELECT materialTypeID, quantity
            FROM BlueprintActivityMaterialRequirements
            WHERE typeID = ? AND activityID = 1
        """, (typeID,))
        return self.cursor.fetchall()

    def calculate_cost(self, typeID, quantity_needed, breakdown=None, level=0):
        indent = "  " * level

        if typeID in self.component_cost_cache:
            unit_cost = self.component_cost_cache[typeID]
            cost = unit_cost * quantity_needed
            if breakdown is not None:
                breakdown.append(f"{indent}{quantity_needed}x {typeID} (cached): {cost:,.2f} ISK")
            return cost

        components = self.get_blueprint_components(typeID)
        if not components:
            cost = self.get_market_price(typeID, quantity_needed)
            if breakdown is not None:
                breakdown.append(f"{indent}{quantity_needed}x {typeID} (market): {cost:,.2f} ISK")
            return cost

        total_cost = 0
        if breakdown is not None:
            breakdown.append(f"{indent}{quantity_needed}x {typeID} (build):")

        for material_typeID, qty_per_unit in components:
            total_qty = qty_per_unit * quantity_needed
            already_used = self.used_materials[material_typeID]
            net_qty = max(0, total_qty - already_used)
            self.used_materials[material_typeID] += total_qty

            cost = self.calculate_cost(material_typeID, net_qty, breakdown, level + 1)
            total_cost += cost

        unit_cost = total_cost / quantity_needed
        self.component_cost_cache[typeID] = unit_cost
        return total_cost

    def reset_state(self):
        self.used_materials.clear()
        self.component_cost_cache.clear()

    def set_region(self, region_id):
        self.selected_region = region_id

    def set_system(self, system_id):
        self.selected_system = system_id


# === GUI Interface ===
class CostCalculatorGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("EVE Production Cost Calculator")

        self.calculator = CostCalculator("F:\Eve Cost Analysis\CostAnalysis.db")

        # Input fields
        ttk.Label(root, text="Item TypeID:").grid(row=0, column=0, sticky="e")
        self.type_entry = ttk.Entry(root, width=20)
        self.type_entry.grid(row=0, column=1)

        ttk.Label(root, text="Quantity:").grid(row=1, column=0, sticky="e")
        self.qty_entry = ttk.Entry(root, width=20)
        self.qty_entry.insert(0, "1")
        self.qty_entry.grid(row=1, column=1)

        ttk.Label(root, text="Region:").grid(row=2, column=0, sticky="e")
        self.region_combo = ttk.Combobox(root, values=["", "10000002", "10000043"], width=18)
        self.region_combo.grid(row=2, column=1)
        self.region_combo.set("")

        ttk.Label(root, text="System:").grid(row=3, column=0, sticky="e")
        self.system_combo = ttk.Combobox(root, values=["", "30000142", "30002187"], width=18)
        self.system_combo.grid(row=3, column=1)
        self.system_combo.set("")

        self.calculate_btn = ttk.Button(root, text="Calculate Cost", command=self.calculate)
        self.calculate_btn.grid(row=4, column=0, columnspan=2, pady=10)

        # Output display
        self.output_box = tk.Text(root, width=70, height=20, wrap="word", state="disabled")
        self.output_box.grid(row=5, column=0, columnspan=2, padx=10, pady=5)

    def calculate(self):
        try:
            typeID = int(self.type_entry.get())
            quantity = int(self.qty_entry.get())

            region_id = self.region_combo.get()
            system_id = self.system_combo.get()

            self.calculator.set_region(int(region_id) if region_id else None)
            self.calculator.set_system(int(system_id) if system_id else None)

            self.calculator.reset_state()
            breakdown = []
            total_cost = self.calculator.calculate_cost(typeID, quantity, breakdown)

            self.output_box.config(state="normal")
            self.output_box.delete("1.0", tk.END)
            self.output_box.insert(tk.END, f"Total cost to build {quantity}x {typeID}: {total_cost:,.2f} ISK\n\n")
            self.output_box.insert(tk.END, "\n".join(breakdown))
            self.output_box.config(state="disabled")

        except Exception as e:
            messagebox.showerror("Error", str(e))

# === Run App ===
if __name__ == "__main__":
    root = tk.Tk()
    app = CostCalculatorGUI(root)
    root.mainloop()
