"""
routes/quality_check.py
--------------------------
USED ON: Quality Check page (finished-good / batch-level QC).

Endpoint:
  POST /api/qc/finished-good
       { batch_id, finished_good_id, qty_inspected, result }  result: 'Pass' | 'Fail'
       -> Update quality counts and dashboard metrics. On a result, the
          matching finished_goods.qc_status is updated to 'Passed' or 'Failed'.
"""

from flask import Blueprint, request, jsonify
from auth import login_required, role_required
from db import get_db_cursor

quality_check_bp = Blueprint("quality_check", __name__)


@quality_check_bp.route("/api/qc/finished-good", methods=["POST"])
@login_required
@role_required("Inventory Inspector", "Supervisor", "Worker")
def record_finished_good_qc():
    data = request.get_json(silent=True) or {}
    batch_id = data.get("batch_id")
    finished_good_id = data.get("finished_good_id")
    product_id_input = data.get("productId") or data.get("product_id")
    qty_inspected = data.get("qty_inspected")
    result = data.get("result")

    # Normalize result
    if result:
        result = result.title()  # e.g., 'PASS' -> 'Pass', 'FAIL' -> 'Fail'

    if result not in ("Pass", "Fail"):
        return jsonify({"error": "result must be 'Pass' or 'Fail'"}), 400

    target_id = batch_id or finished_good_id or product_id_input
    if not target_id:
        return jsonify({"error": "An ID (batch_id, finished_good_id, or product_id) is required"}), 400

    with get_db_cursor(commit=True) as cur:
        # 1. Resolve batch_id and finished_good_id
        resolved_batch_id = None
        resolved_finished_good_id = None

        # Check if target_id matches a finished_goods record
        cur.execute("SELECT finished_good_id, batch_id FROM finished_goods WHERE finished_good_id = %s", (target_id,))
        fg_row = cur.fetchone()
        if fg_row:
            resolved_finished_good_id = fg_row["finished_good_id"]
            resolved_batch_id = fg_row["batch_id"]
        else:
            # Check if it matches a production batch
            cur.execute("SELECT batch_id FROM production_batches WHERE batch_id = %s", (target_id,))
            pb_row = cur.fetchone()
            if pb_row:
                resolved_batch_id = pb_row["batch_id"]
                # See if there's an associated finished good
                cur.execute("SELECT finished_good_id FROM finished_goods WHERE batch_id = %s", (resolved_batch_id,))
                fg_assoc = cur.fetchone()
                if fg_assoc:
                    resolved_finished_good_id = fg_assoc["finished_good_id"]
            else:
                return jsonify({"error": f"ID '{target_id}' could not be matched to any batch or finished good"}), 404

        # If qty_inspected not passed, default to completed_qty of the batch
        if not qty_inspected:
            cur.execute("SELECT completed_qty, target_qty FROM production_batches WHERE batch_id = %s", (resolved_batch_id,))
            batch_row = cur.fetchone()
            if batch_row:
                qty_inspected = batch_row["completed_qty"] or batch_row["target_qty"] or 1
            else:
                qty_inspected = 1

        # 2. Record inspection
        cur.execute("""
            INSERT INTO quality_check (inspection_type, finished_good_id, batch_id, qty_checked, result)
            VALUES ('Finished Good', %s, %s, %s, %s)
        """, (resolved_finished_good_id, resolved_batch_id, qty_inspected, result))
        inspection_id = cur.lastrowid

        # 3. Update Finished Goods status if one exists
        updated_finished_good = None
        if resolved_finished_good_id:
            new_qc_status = "Passed" if result == "Pass" else "Failed"
            cur.execute("""
                UPDATE finished_goods SET qc_status = %s WHERE finished_good_id = %s
            """, (new_qc_status, resolved_finished_good_id))
            updated_finished_good = {"finished_good_id": resolved_finished_good_id, "qc_status": new_qc_status}

            # Update final QC stage in batch_stages
            cur.execute("""
                SELECT stage_id FROM batch_stages
                WHERE batch_id = %s
                ORDER BY stage_id DESC LIMIT 1
            """, (resolved_batch_id,))
            final_stage_row = cur.fetchone()
            if final_stage_row:
                cur.execute("""
                    UPDATE batch_stages
                    SET status = 'Complete', end_timestamp = CURRENT_TIMESTAMP,
                        actual_hours = TIMESTAMPDIFF(MINUTE, COALESCE(start_timestamp, CURRENT_TIMESTAMP), CURRENT_TIMESTAMP) / 60
                    WHERE stage_id = %s
                """, (final_stage_row["stage_id"],))

        # Refresh dashboard-facing quality counts for this batch
        cur.execute("""
            SELECT
                SUM(CASE WHEN result = 'Pass' THEN 1 ELSE 0 END) AS passed_count,
                SUM(CASE WHEN result = 'Fail' THEN 1 ELSE 0 END) AS failed_count
            FROM quality_check
            WHERE batch_id = %s AND inspection_type = 'Finished Good'
        """, (resolved_batch_id,))
        quality_counts = cur.fetchone()

    return jsonify({
        "message": "Quality check recorded",
        "inspection_id": inspection_id,
        "batch_id": resolved_batch_id,
        "result": result,
        "finished_good": updated_finished_good,
        "quality_counts": quality_counts,
    }), 201


@quality_check_bp.route("/api/qc/pending-batches", methods=["GET"])
@login_required
def get_pending_qc_batches():
    with get_db_cursor() as cur:
        cur.execute("""
            SELECT fg.finished_good_id, fg.batch_id, p.product_name
            FROM finished_goods fg
            JOIN products p ON fg.product_id = p.product_id
            WHERE fg.qc_status = 'Pending QC'
            ORDER BY fg.generation_date DESC
        """)
        batches = cur.fetchall()
    return jsonify({"batches": batches}), 200
