"""
routes/raw_material_requests.py
---------------------------------
USED ON: Raw Material Requests page.

Endpoint:
  PATCH /api/material-requests/<request_id>
        { action: 'approve' | 'fulfil' }
        -> Update request status. On 'fulfil', the request moves to
           Raw Material QC by creating a Material_Transfers record
           ('In Transit') that the Floor Material Intake page later verifies.
"""

from flask import Blueprint, request, jsonify
from auth import login_required, role_required
from db import get_db_cursor

raw_material_requests_bp = Blueprint("raw_material_requests", __name__)

VALID_ACTIONS = {
    "approve": "Approved",
    "fulfil": "Fulfilled",
    "reject": "Rejected",
}


@raw_material_requests_bp.route("/api/material-requests/<int:request_id>", methods=["PATCH"])
@login_required
@role_required("Supervisor", "Inventory Inspector")
def update_material_request(request_id):
    data = request.get_json(silent=True) or {}
    action = data.get("action")

    if action not in VALID_ACTIONS:
        return jsonify({"error": f"action must be one of {list(VALID_ACTIONS.keys())}"}), 400

    with get_db_cursor(commit=True) as cur:
        cur.execute("SELECT * FROM Material_Requests WHERE request_id = %s FOR UPDATE", (request_id,))
        req = cur.fetchone()
        if not req:
            return jsonify({"error": f"No material request with id {request_id}"}), 404

        new_status = VALID_ACTIONS[action]
        cur.execute("""
            UPDATE Material_Requests SET status = %s WHERE request_id = %s
        """, (new_status, request_id))

        transfer_id = None
        if action == "fulfil":
            # Moves the request into the Raw Material QC pipeline
            cur.execute("""
                INSERT INTO Material_Transfers (component_id, dispatched_qty, transfer_status)
                VALUES (%s, %s, 'In Transit')
            """, (req["component_id"], req["requested_qty"]))
            transfer_id = cur.lastrowid

            cur.execute("""
                UPDATE Components SET warehouse_stock = warehouse_stock - %s
                WHERE component_id = %s
            """, (req["requested_qty"], req["component_id"]))

    response = {
        "message": f"Material request {request_id} {new_status.lower()}",
        "request_id": request_id,
        "status": new_status,
    }
    if transfer_id:
        response["transfer_id"] = transfer_id
        response["moved_to"] = "Raw Material QC"

    return jsonify(response), 200
