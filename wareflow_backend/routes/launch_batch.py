"""
routes/launch_batch.py
-----------------------
USED ON: Launch Batch page.

Endpoints:
  POST /api/batches
       { product_name, target_qty }
       -> Generate Batch ID, create batch record, initialize
          completed_qty = 0 and status = 'Initialized'.

  POST /api/batches/<batch_id>/stages
       { stages: [ { stage_name, target_hours }, ... ] }
       -> Create/update Batch_Stages records and store target values.
"""

import uuid
from flask import Blueprint, request, jsonify
from auth import login_required, role_required
from db import get_db_cursor

launch_batch_bp = Blueprint("launch_batch", __name__)


def _generate_batch_id() -> str:
    return f"BATCH-{uuid.uuid4().hex[:8].upper()}"


@launch_batch_bp.route("/api/batches", methods=["POST"])
@login_required
@role_required("Supervisor", "Worker")
def initialize_batch():
    data = request.get_json(silent=True) or {}
    product_name = data.get("product_name")
    target_qty = data.get("target_qty")

    if not product_name or not target_qty:
        return jsonify({"error": "product_name and target_qty are required"}), 400

    batch_id = _generate_batch_id()

    with get_db_cursor(commit=True) as cur:
        cur.execute("""
            INSERT INTO Production_Batches (batch_id, product_name, target_qty, completed_qty, status)
            VALUES (%s, %s, %s, 0, 'Initialized')
        """, (batch_id, product_name, target_qty))

    return jsonify({
        "message": "Batch initialized",
        "batch_id": batch_id,
        "product_name": product_name,
        "target_qty": target_qty,
        "completed_qty": 0,
        "status": "Initialized",
    }), 201


@launch_batch_bp.route("/api/batches/<batch_id>/stages", methods=["POST"])
@login_required
@role_required("Supervisor", "Worker")
def set_batch_stages(batch_id):
    data = request.get_json(silent=True) or {}
    stages = data.get("stages")

    if not stages or not isinstance(stages, list):
        return jsonify({"error": "stages must be a non-empty list of {stage_name, target_hours}"}), 400

    with get_db_cursor(commit=True) as cur:
        cur.execute("SELECT batch_id FROM Production_Batches WHERE batch_id = %s", (batch_id,))
        if not cur.fetchone():
            return jsonify({"error": f"Unknown batch_id '{batch_id}'"}), 404

        created_or_updated = []
        for stage in stages:
            stage_name = stage.get("stage_name")
            target_hours = stage.get("target_hours")
            if not stage_name or target_hours is None:
                continue

            cur.execute("""
                SELECT stage_id FROM Batch_Stages
                WHERE batch_id = %s AND stage_name = %s
            """, (batch_id, stage_name))
            existing = cur.fetchone()

            if existing:
                cur.execute("""
                    UPDATE Batch_Stages SET target_hours = %s
                    WHERE stage_id = %s
                """, (target_hours, existing["stage_id"]))
                created_or_updated.append({"stage_id": existing["stage_id"], "stage_name": stage_name, "action": "updated"})
            else:
                cur.execute("""
                    INSERT INTO Batch_Stages (batch_id, stage_name, target_hours, status)
                    VALUES (%s, %s, %s, 'In Progress')
                """, (batch_id, stage_name, target_hours))
                created_or_updated.append({"stage_id": cur.lastrowid, "stage_name": stage_name, "action": "created"})

    return jsonify({"batch_id": batch_id, "stages": created_or_updated}), 200
