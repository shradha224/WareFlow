"""
routes/quality_check.py
--------------------------
USED ON: Quality Check page (finished-good / batch-level QC).

Endpoint:
  POST /api/qc/finished-good
       { batch_id, finished_good_id, qty_inspected, result }  result: 'Pass' | 'Fail'
       -> Update quality counts and dashboard metrics. On a result, the
          matching Finished_Goods.qc_status is updated to 'Passed' or 'Failed'.
"""

from flask import Blueprint, request, jsonify
from auth import login_required, role_required
from db import get_db_cursor

quality_check_bp = Blueprint("quality_check", __name__)


@quality_check_bp.route("/api/qc/finished-good", methods=["POST"])
@login_required
@role_required("Inventory Inspector", "Supervisor")
def record_finished_good_qc():
    data = request.get_json(silent=True) or {}
    batch_id = data.get("batch_id")
    finished_good_id = data.get("finished_good_id")
    qty_inspected = data.get("qty_inspected")
    result = data.get("result")

    if not batch_id or not qty_inspected or result not in ("Pass", "Fail"):
        return jsonify({"error": "batch_id, qty_inspected, and result ('Pass'/'Fail') are required"}), 400

    with get_db_cursor(commit=True) as cur:
        cur.execute("SELECT batch_id FROM Production_Batches WHERE batch_id = %s", (batch_id,))
        if not cur.fetchone():
            return jsonify({"error": f"Unknown batch_id '{batch_id}'"}), 404

        cur.execute("""
            INSERT INTO Quality_Inspections (batch_id, qty_inspected, result)
            VALUES (%s, %s, %s)
        """, (batch_id, qty_inspected, result))
        inspection_id = cur.lastrowid

        updated_finished_good = None
        if finished_good_id:
            cur.execute("SELECT finished_good_id FROM Finished_Goods WHERE finished_good_id = %s", (finished_good_id,))
            if cur.fetchone():
                new_qc_status = "Passed" if result == "Pass" else "Failed"
                cur.execute("""
                    UPDATE Finished_Goods SET qc_status = %s WHERE finished_good_id = %s
                """, (new_qc_status, finished_good_id))
                updated_finished_good = {"finished_good_id": finished_good_id, "qc_status": new_qc_status}

        # Refresh dashboard-facing quality counts for this batch
        cur.execute("""
            SELECT
                SUM(CASE WHEN result = 'Pass' THEN 1 ELSE 0 END) AS passed_count,
                SUM(CASE WHEN result = 'Fail' THEN 1 ELSE 0 END) AS failed_count
            FROM Quality_Inspections
            WHERE batch_id = %s
        """, (batch_id,))
        quality_counts = cur.fetchone()

    return jsonify({
        "message": "Quality check recorded",
        "inspection_id": inspection_id,
        "batch_id": batch_id,
        "result": result,
        "finished_good": updated_finished_good,
        "quality_counts": quality_counts,
    }), 201
