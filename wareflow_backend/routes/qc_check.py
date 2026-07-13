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


@qc_check_bp.route("/api/qc/component", methods=["POST"])
@login_required
@role_required("Inventory Inspector", "Supervisor")
def record_component_qc():
    data = request.get_json(silent=True) or {}
    component_id = data.get("component_id")
    qty_inspected = data.get("qty_inspected")
    result = data.get("result")

    if not component_id or not qty_inspected or result not in ("Pass", "Fail"):
        return jsonify({"error": "component_id, qty_inspected, and result ('Pass'/'Fail') are required"}), 400

    with get_db_cursor(commit=True) as cur:
        cur.execute("SELECT warehouse_stock FROM Components WHERE component_id = %s FOR UPDATE", (component_id,))
        comp = cur.fetchone()
        if not comp:
            return jsonify({"error": f"Unknown component_id '{component_id}'"}), 404

        cur.execute("""
            INSERT INTO Quality_Inspections (component_id, qty_inspected, result)
            VALUES (%s, %s, %s)
        """, (component_id, qty_inspected, result))
        inspection_id = cur.lastrowid

        if result == "Fail":
            # Rejected units are pulled out of usable warehouse stock
            new_stock = max(0, comp["warehouse_stock"] - qty_inspected)
            cur.execute("""
                UPDATE Components SET warehouse_stock = %s WHERE component_id = %s
            """, (new_stock, component_id))

        # Refresh quality metrics for this component
        cur.execute("""
            SELECT
                SUM(CASE WHEN result = 'Pass' THEN qty_inspected ELSE 0 END) AS total_passed,
                SUM(CASE WHEN result = 'Fail' THEN qty_inspected ELSE 0 END) AS total_failed
            FROM Quality_Inspections
            WHERE component_id = %s
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
