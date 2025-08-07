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

    def get_market_price(self, typeID, quantity):
        self.cursor.execute("""
            SELECT price FROM MarketOrdersAll
            WHERE typeID = ? AND buy_true_sell_false = 0
            ORDER BY price ASC, dateIssued DESC
            LIMIT 1
        """, (typeID,))
        row = self.cursor.fetchone()
        if row:
            return row[0] * quantity
        else:
            return float('inf')  # Unavailable

    def get_blueprint_components(self, typeID):
        self.cursor.execute("""
            SELECT materialTypeID, quantity
            FROM BlueprintActivityMaterialRequirements
            WHERE typeID = ? AND activityID = 1
        """, (typeID,))
        return self.cursor.fetchall()

    def calculate_cost(self, typeID, quantity_needed):
        if typeID in self.component_cost_cache:
            return self.component_cost_cache[typeID] * quantity_needed

        components = self.get_blueprint_components(typeID)
        if not components:
            cost = self.get_market_price(typeID, quantity_needed)
            return cost

        total_cost = 0
        for material_typeID, qty_per_unit in components:
            total_qty = qty_per_unit * quantity_needed

            already_used = self.used_materials[material_typeID]
            net_qty = max(0, total_qty - already_used)

            self.used_materials[material_typeID] += total_qty

            material_cost = self.calculate_cost(material_typeID, net_qty)
            total_cost += material_cost

        unit_cost = total_cost / quantity_needed
        self.component_cost_cache[typeID] = unit_cost
        return total_cost

    def reset_state(self):
        self.used_materials.clear()
        self.component_cost_cache.clear()

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

        self.calculate_btn = ttk.Button(root, text="Calculate Cost", command=self.calculate)
        self.calculate_btn.grid(row=2, column=0, columnspan=2, pady=10)

        # Output display
        self.output_box = tk.Text(root, width=60, height=10, wrap="word", state="disabled")
        self.output_box.grid(row=3, column=0, columnspan=2, padx=10, pady=5)

    def calculate(self):
        try:
            typeID = int(self.type_entry.get())
            quantity = int(self.qty_entry.get())
            self.calculator.reset_state()
            cost = self.calculator.calculate_cost(typeID, quantity)

            self.output_box.config(state="normal")
            self.output_box.delete("1.0", tk.END)
            self.output_box.insert(tk.END, f"Total cost to build {quantity}x {typeID}: {cost:,.2f} ISK")
            self.output_box.config(state="disabled")

        except Exception as e:
            messagebox.showerror("Error", str(e))

# === Run App ===
if __name__ == "__main__":
    root = tk.Tk()
    app = CostCalculatorGUI(root)
    root.mainloop()
