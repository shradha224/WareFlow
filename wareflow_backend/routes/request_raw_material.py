"""
routes/request_raw_material.py
--------------------------------
USED ON: Request Raw Material page.

Endpoint:
  POST /api/material-requests
       { component_id, requested_qty }
       -> Generate Request ID, create request record, set Pending status.
"""

from flask import Blueprint, request, jsonify, g
from auth import login_required
from db import get_db_cursor

request_raw_material_bp = Blueprint("request_raw_material", __name__)
@request_raw_material_bp.route("/api/components", methods=["GET"])
def get_components():
    with get_db_cursor() as cur:
        cur.execute("""
            SELECT component_id, part_name
            FROM components
            ORDER BY part_name
        """)

        components = cur.fetchall()

    return jsonify({"components": components}), 200

@request_raw_material_bp.route("/api/material-requests", methods=["POST"])
@login_required
def submit_material_request():
    data = request.get_json(silent=True) or {}
    component_id = data.get("component_id")
    requested_qty = data.get("requested_qty")

    if not component_id or not requested_qty:
        return jsonify({"error": "component_id and requested_qty are required"}), 400
    if requested_qty <= 0:
        return jsonify({"error": "requested_qty must be positive"}), 400

    with get_db_cursor(commit=True) as cur:
        cur.execute("SELECT component_id FROM components WHERE component_id = %s", (component_id,))
        if not cur.fetchone():
            return jsonify({"error": f"Unknown component_id '{component_id}'"}), 404

        cur.execute("""
            INSERT INTO material_requests (component_id, requested_qty, status)
            VALUES (%s, %s, 'Pending')
        """, (component_id, requested_qty))
        request_id = cur.lastrowid

    return jsonify({
        "message": "Material request submitted",
        "request_id": request_id,
        "component_id": component_id,
        "requested_qty": requested_qty,
        "status": "Pending",
        "submitted_by": g.user_id,
    }), 201
