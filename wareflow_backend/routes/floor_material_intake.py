"""
routes/floor_material_intake.py
---------------------------------
USED ON: Floor Material Intake page.

Endpoint:
  PATCH /api/transfers/<transfer_id>/verify
        -> Update transfer status to 'Received', store received_at
           timestamp, and add the dispatched quantity onto the floor stock.
"""

from flask import Blueprint, jsonify
from auth import login_required, role_required
from db import get_db_cursor

floor_material_intake_bp = Blueprint("floor_material_intake", __name__)


@floor_material_intake_bp.route("/api/transfers/<int:transfer_id>/verify", methods=["PATCH"])
@login_required
@role_required("Worker", "Inventory Inspector")
def verify_received(transfer_id):
    with get_db_cursor(commit=True) as cur:
        cur.execute("SELECT * FROM Material_Transfers WHERE transfer_id = %s FOR UPDATE", (transfer_id,))
        transfer = cur.fetchone()
        if not transfer:
            return jsonify({"error": f"No transfer with id {transfer_id}"}), 404
        if transfer["transfer_status"] == "Received":
            return jsonify({"error": "Transfer already marked as received"}), 409

        cur.execute("""
            UPDATE Material_Transfers
            SET transfer_status = 'Received', received_at = CURRENT_TIMESTAMP
            WHERE transfer_id = %s
        """, (transfer_id,))

        cur.execute("""
            UPDATE Components SET floor_stock = floor_stock + %s
            WHERE component_id = %s
        """, (transfer["dispatched_qty"], transfer["component_id"]))

    return jsonify({
        "message": "Transfer verified as received",
        "transfer_id": transfer_id,
        "component_id": transfer["component_id"],
        "qty_added_to_floor_stock": transfer["dispatched_qty"],
    }), 200
