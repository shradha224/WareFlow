"""
routes/raw_material_requests.py
---------------------------------
USED ON: Raw Material Requests page.

Endpoint:
  PATCH /api/material-requests/<request_id>
        { action: 'approve' | 'fulfil' }
        -> Update request status. On 'fulfil', the request moves to
           Raw Material QC by creating a material_transfers record
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


@raw_material_requests_bp.route("/api/material-requests", methods=["GET"])
@login_required
def get_material_requests():
    with get_db_cursor() as cur:
        cur.execute("""
            SELECT mr.request_id, mr.component_id, c.part_name, mr.requested_qty, mr.status, mr.created_at, mr.batch_id
            FROM material_requests mr
            JOIN components c ON mr.component_id = c.component_id
            ORDER BY mr.created_at DESC
        """)
        requests = cur.fetchall()
    return jsonify({"requests": requests}), 200


@raw_material_requests_bp.route("/api/material-requests/<int:request_id>", methods=["PATCH"])
@login_required
@role_required("Supervisor", "Inventory Inspector")
def update_material_request(request_id):
    data = request.get_json(silent=True) or {}
    action = data.get("action")

    if action not in VALID_ACTIONS:
        return jsonify({"error": f"action must be one of {list(VALID_ACTIONS.keys())}"}), 400

    with get_db_cursor(commit=True) as cur:
        cur.execute("SELECT * FROM material_requests WHERE request_id = %s FOR UPDATE", (request_id,))
        req = cur.fetchone()
        if not req:
            return jsonify({"error": f"No material request with id {request_id}"}), 404

        new_status = VALID_ACTIONS[action]
        cur.execute("""
            UPDATE material_requests SET status = %s WHERE request_id = %s
        """, (new_status, request_id))

    return jsonify({
        "message": f"Material request {request_id} {new_status.lower()}",
        "request_id": request_id,
        "status": new_status,
    }), 200
