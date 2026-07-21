"""
routes/warehouse_stock_control.py
-----------------------------------
USED ON: Warehouse Stock Control page.

Endpoints:
  POST /api/stock/dispatch
       { component_id, dispatched_qty }
       -> Reduce warehouse stock and create a material_transfers record
          (transfer_status = 'In Transit'). This is the schema's
          equivalent of the spec's "FloorHouseInventory record".

  POST /api/inventory/items
       { part_name, description, min_threshold, warehouse_stock, floor_stock }
       -> Generate Component ID and create inventory record.
"""

import uuid
from flask import Blueprint, request, jsonify
from auth import login_required, role_required
from db import get_db_cursor

warehouse_stock_control_bp = Blueprint("warehouse_stock_control", __name__)


def _generate_component_id() -> str:
    return f"COMP-{uuid.uuid4().hex[:8].upper()}"


@warehouse_stock_control_bp.route("/api/stock/dispatch", methods=["POST"])
@login_required
@role_required("Supervisor", "Inventory Inspector")
def dispatch_material():
    data = request.get_json(silent=True) or {}
    component_id = data.get("component_id")
    dispatched_qty = data.get("dispatched_qty")

    if not component_id or not dispatched_qty:
        return jsonify({"error": "component_id and dispatched_qty are required"}), 400
    if dispatched_qty <= 0:
        return jsonify({"error": "dispatched_qty must be positive"}), 400

    with get_db_cursor(commit=True) as cur:
        cur.execute(
            "SELECT warehouse_stock FROM components WHERE component_id = %s FOR UPDATE",
            (component_id,),
        )
        row = cur.fetchone()
        if not row:
            return jsonify({"error": f"Unknown component_id '{component_id}'"}), 404
        if row["warehouse_stock"] < dispatched_qty:
            return jsonify({
                "error": "Insufficient warehouse stock",
                "available": row["warehouse_stock"],
                "requested": dispatched_qty,
            }), 409

        cur.execute("""
            UPDATE components SET warehouse_stock = warehouse_stock - %s
            WHERE component_id = %s
        """, (dispatched_qty, component_id))

        cur.execute("""
            INSERT INTO material_transfers (component_id, dispatched_qty, transfer_status)
            VALUES (%s, %s, 'In Transit')
        """, (component_id, dispatched_qty))
        transfer_id = cur.lastrowid

    return jsonify({
        "message": "Material dispatched",
        "transfer_id": transfer_id,
        "component_id": component_id,
        "dispatched_qty": dispatched_qty,
        "transfer_status": "In Transit",
    }), 201


@warehouse_stock_control_bp.route("/api/inventory/items", methods=["POST"])
@login_required
@role_required("Supervisor", "Inventory Inspector")
def add_new_item():
    data = request.get_json(silent=True) or {}
    part_name = data.get("part_name")
    description = data.get("description", "")
    min_threshold = data.get("min_threshold")
    warehouse_stock = data.get("warehouse_stock", 0)
    floor_stock = data.get("floor_stock", 0)

    if not part_name or min_threshold is None:
        return jsonify({"error": "part_name and min_threshold are required"}), 400

    component_id = _generate_component_id()

    with get_db_cursor(commit=True) as cur:
        cur.execute("""
            INSERT INTO components
                (component_id, part_name, description, warehouse_stock, floor_stock, min_threshold)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (component_id, part_name, description, warehouse_stock, floor_stock, min_threshold))

    return jsonify({
        "message": "Inventory item created",
        "component_id": component_id,
        "part_name": part_name,
        "description": description,
        "warehouse_stock": warehouse_stock,
        "floor_stock": floor_stock,
        "min_threshold": min_threshold,
    }), 201


@warehouse_stock_control_bp.route("/api/batches/<batch_id>/dispatch", methods=["POST"])
@login_required
@role_required("Supervisor", "Inventory Inspector")
def dispatch_batch_materials(batch_id):
    with get_db_cursor(commit=True) as cur:
        cur.execute("SELECT pb.*, p.product_name FROM production_batches pb JOIN products p ON pb.product_id = p.product_id WHERE pb.batch_id = %s FOR UPDATE", (batch_id,))
        batch = cur.fetchone()
        if not batch:
            return jsonify({"error": f"Unknown batch '{batch_id}'"}), 404
        if batch["status"] in ("Complete", "Completed"):
            return jsonify({"error": "Cannot dispatch materials for a completed batch"}), 400

        cur.execute("SELECT component_id, quantity_required FROM junction_of_materials WHERE product_id = %s", (batch["product_id"],))
        bom = cur.fetchall()
        if not bom:
            return jsonify({"error": f"No component mapping found for product {batch['product_name']}"}), 400

        components_to_dispatch = []
        for item in bom:
            req_qty = item["quantity_required"] * batch["target_qty"]
            
            # Check already transferred
            cur.execute("""
                SELECT SUM(dispatched_qty) AS dispatched 
                FROM material_transfers 
                WHERE batch_id = %s AND component_id = %s
            """, (batch_id, item["component_id"]))
            transferred = cur.fetchone()["dispatched"] or 0
            
            # Check pending requests
            cur.execute("""
                SELECT SUM(requested_qty) AS requested 
                FROM material_requests 
                WHERE batch_id = %s AND component_id = %s AND status = 'Pending'
            """, (batch_id, item["component_id"]))
            requested = cur.fetchone()["requested"] or 0
            
            to_dispatch = req_qty - (transferred + requested)
            if to_dispatch <= 0:
                # Already fully covered
                continue
                
            cur.execute("SELECT warehouse_stock, part_name FROM components WHERE component_id = %s FOR UPDATE", (item["component_id"],))
            comp = cur.fetchone()
            if not comp:
                return jsonify({"error": f"Unknown component '{item['component_id']}'"}), 404
            if comp["warehouse_stock"] < to_dispatch:
                return jsonify({
                    "error": f"Insufficient stock for component '{comp['part_name']} ({item['component_id']})': required {to_dispatch}, available {comp['warehouse_stock']}"
                }), 409
                
            components_to_dispatch.append({
                "component_id": item["component_id"],
                "qty": to_dispatch
            })

        if not components_to_dispatch:
            return jsonify({"error": "Materials already fully dispatched for this batch"}), 409

        transfers = []
        for item in components_to_dispatch:
            cur.execute("""
                UPDATE components SET warehouse_stock = warehouse_stock - %s
                WHERE component_id = %s
            """, (item["qty"], item["component_id"]))

            cur.execute("""
                INSERT INTO material_transfers (component_id, dispatched_qty, transfer_status, batch_id)
                VALUES (%s, %s, 'In Transit', %s)
            """, (item["component_id"], item["qty"], batch_id))
            transfers.append({
                "transfer_id": cur.lastrowid,
                "component_id": item["component_id"],
                "dispatched_qty": item["qty"],
                "transfer_status": "In Transit"
            })

        cur.execute("UPDATE production_batches SET status = 'Dispatched' WHERE batch_id = %s", (batch_id,))

    return jsonify({
        "message": f"Materials successfully dispatched for batch {batch_id}",
        "batch_id": batch_id,
        "transfers": transfers
    }), 201
