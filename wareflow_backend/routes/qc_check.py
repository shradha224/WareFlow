"""
routes/qc_check.py
--------------------
USED ON: QC Check page (incoming component / raw-material inspection).

Endpoint:
  POST /api/qc/component
       { component_id, qty_inspected, result }   result: 'Pass' | 'Fail'
       -> Store QC result and update quality metrics. Failed units are
          removed from usable warehouse stock.
"""

from flask import Blueprint, request, jsonify
from auth import login_required, role_required
from db import get_db_cursor

qc_check_bp = Blueprint("qc_check", __name__)


@qc_check_bp.route("/api/qc/pending", methods=["GET"])
@login_required
@role_required("Inventory Inspector", "Supervisor")
def get_pending_qc_components():
    with get_db_cursor() as cur:
        cur.execute("""
            SELECT mr.request_id, mr.component_id, c.part_name, mr.requested_qty, mr.created_at, mr.batch_id
            FROM material_requests mr
            JOIN components c ON mr.component_id = c.component_id
            WHERE mr.status IN ('Approved', 'Fulfilled')
            ORDER BY mr.created_at DESC
        """)
        pending = cur.fetchall()
    return jsonify({"pending": pending}), 200


@qc_check_bp.route("/api/qc/component", methods=["POST"])
@login_required
@role_required("Inventory Inspector", "Supervisor")
def record_component_qc():
    data = request.get_json(silent=True) or {}
    component_id = data.get("component_id")
    qty_inspected = data.get("qty_inspected")
    result = data.get("result")
    request_id = data.get("request_id")

    if not component_id or not qty_inspected or result not in ("Pass", "Fail"):
        return jsonify({"error": "component_id, qty_inspected, and result ('Pass'/'Fail') are required"}), 400

    with get_db_cursor(commit=True) as cur:
        cur.execute("SELECT warehouse_stock FROM components WHERE component_id = %s FOR UPDATE", (component_id,))
        comp = cur.fetchone()
        if not comp:
            return jsonify({"error": f"Unknown component_id '{component_id}'"}), 404

        batch_id = None
        if request_id:
            cur.execute("SELECT batch_id FROM material_requests WHERE request_id = %s", (request_id,))
            req_row = cur.fetchone()
            if req_row:
                batch_id = req_row["batch_id"]

        cur.execute("""
            INSERT INTO quality_check (inspection_type, component_id, batch_id, qty_checked, result)
            VALUES ('Raw Material', %s, %s, %s, %s)
        """, (component_id, batch_id, qty_inspected, result))
        inspection_id = cur.lastrowid

        if result == "Pass":
            cur.execute("""
                UPDATE components SET warehouse_stock = warehouse_stock + %s
                WHERE component_id = %s
            """, (qty_inspected, component_id))
        else:
            if not request_id:
                new_stock = max(0, comp["warehouse_stock"] - qty_inspected)
                cur.execute("""
                    UPDATE components SET warehouse_stock = %s WHERE component_id = %s
                """, (new_stock, component_id))

        if request_id:
            new_status = "QC Passed" if result == "Pass" else "QC Failed"
            cur.execute("""
                UPDATE material_requests SET status = %s WHERE request_id = %s
            """, (new_status, request_id))

        # Refresh quality metrics for this component
        cur.execute("""
            SELECT
                SUM(CASE WHEN result = 'Pass' THEN qty_checked ELSE 0 END) AS total_passed,
                SUM(CASE WHEN result = 'Fail' THEN qty_checked ELSE 0 END) AS total_failed
            FROM quality_check
            WHERE component_id = %s AND inspection_type = 'Raw Material'
        """, (component_id,))
        metrics = cur.fetchone()

    return jsonify({
        "message": "QC result recorded",
        "inspection_id": inspection_id,
        "component_id": component_id,
        "result": result,
        "qty_inspected": qty_inspected,
        "quality_metrics": metrics,
    }), 201
