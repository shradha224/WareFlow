"""
routes/warehouse_inventory.py
------------------------------
USED ON: Warehouse Inventory page.

Endpoint:
  GET /api/inventory
      -> Retrieve inventory records and calculate stock status
         (Low / Adequate) for each component.
"""

from flask import Blueprint, jsonify
from auth import login_required
from db import get_db_cursor

warehouse_inventory_bp = Blueprint("warehouse_inventory", __name__)


@warehouse_inventory_bp.route("/api/inventory", methods=["GET"])
@login_required
def get_inventory():
    with get_db_cursor() as cur:
        cur.execute("""
            SELECT component_id, part_name, description,
                   warehouse_stock, floor_stock, min_threshold
            FROM Components
            ORDER BY part_name
        """)
        components = cur.fetchall()

    for c in components:
        total_stock = c["warehouse_stock"] + c["floor_stock"]
        c["total_stock"] = total_stock
        c["stock_status"] = "Low" if total_stock < c["min_threshold"] else "Adequate"

    return jsonify({"inventory": components}), 200
