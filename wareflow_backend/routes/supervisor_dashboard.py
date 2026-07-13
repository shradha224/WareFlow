"""
routes/supervisor_dashboard.py
-------------------------------
USED ON: Supervisor Dashboard page.

Endpoints:
  GET  /api/dashboard/supervisor
       -> Fetch active alerts count, pending requests, QC percentages,
          batch progress, workload summaries, demand prediction data.

  POST /api/dashboard/supervisor/place-order
       { component_id, requested_qty }
       -> Generate a raw material request automatically and set
          status = Pending (fired from a low-stock alert card).
"""

from flask import Blueprint, request, jsonify, g
from auth import login_required, role_required
from db import get_db_cursor

supervisor_bp = Blueprint("supervisor_dashboard", __name__)


@supervisor_bp.route("/api/dashboard/supervisor", methods=["GET"])
@login_required
@role_required("Supervisor")
def supervisor_dashboard():
    with get_db_cursor() as cur:
        # Active alerts: components under their minimum threshold
        cur.execute("""
            SELECT component_id, part_name, warehouse_stock, floor_stock, min_threshold
            FROM Components
            WHERE (warehouse_stock + floor_stock) < min_threshold
        """)
        low_stock_alerts = cur.fetchall()

        # Pending material requests
        cur.execute("SELECT COUNT(*) AS pending_count FROM Material_Requests WHERE status = 'Pending'")
        pending_requests = cur.fetchone()["pending_count"]

        # QC pass percentage (component + finished good inspections combined)
        cur.execute("""
            SELECT
                SUM(CASE WHEN result = 'Pass' THEN 1 ELSE 0 END) AS passed,
                COUNT(*) AS total
            FROM Quality_Inspections
        """)
        qc_row = cur.fetchone()
        qc_pass_percentage = (
            round((qc_row["passed"] or 0) / qc_row["total"] * 100, 2)
            if qc_row["total"] else None
        )

        # Batch progress: completed_qty vs target_qty for active batches
        cur.execute("""
            SELECT batch_id, product_name, target_qty, completed_qty, status,
                   ROUND(completed_qty / target_qty * 100, 2) AS percent_complete
            FROM Production_Batches
            WHERE status != 'Complete'
        """)
        batch_progress = cur.fetchall()

        # Workload summary: batch count grouped by status, and stage backlog
        cur.execute("""
            SELECT status, COUNT(*) AS batch_count
            FROM Production_Batches
            GROUP BY status
        """)
        workload_by_status = cur.fetchall()

        cur.execute("""
            SELECT stage_name, COUNT(*) AS in_progress_count
            FROM Batch_Stages
            WHERE status = 'In Progress'
            GROUP BY stage_name
        """)
        workload_by_stage = cur.fetchall()

        # Latest demand prediction data (most recent forecast per component)
        cur.execute("""
            SELECT df.component_id, c.part_name, df.predicted_demand_qty,
                   df.forecast_period_start, df.forecast_period_end, df.generated_at
            FROM Demand_Forecasts df
            JOIN Components c ON c.component_id = df.component_id
            WHERE df.forecast_id IN (
                SELECT MAX(forecast_id) FROM Demand_Forecasts GROUP BY component_id
            )
        """)
        demand_forecasts = cur.fetchall()

    return jsonify({
        "active_alerts": {
            "count": len(low_stock_alerts),
            "items": low_stock_alerts,
        },
        "pending_requests": pending_requests,
        "qc_pass_percentage": qc_pass_percentage,
        "batch_progress": batch_progress,
        "workload_summary": {
            "by_status": workload_by_status,
            "by_stage": workload_by_stage,
        },
        "demand_forecasts": demand_forecasts,
    }), 200


@supervisor_bp.route("/api/dashboard/supervisor/place-order", methods=["POST"])
@login_required
@role_required("Supervisor")
def place_order_from_alert():
    data = request.get_json(silent=True) or {}
    component_id = data.get("component_id")
    requested_qty = data.get("requested_qty")

    if not component_id or not requested_qty:
        return jsonify({"error": "component_id and requested_qty are required"}), 400

    with get_db_cursor(commit=True) as cur:
        cur.execute("SELECT component_id FROM Components WHERE component_id = %s", (component_id,))
        if not cur.fetchone():
            return jsonify({"error": f"Unknown component_id '{component_id}'"}), 404

        cur.execute("""
            INSERT INTO Material_Requests (component_id, requested_qty, status)
            VALUES (%s, %s, 'Pending')
        """, (component_id, requested_qty))
        request_id = cur.lastrowid

    return jsonify({
        "message": "Material request generated",
        "request_id": request_id,
        "component_id": component_id,
        "requested_qty": requested_qty,
        "status": "Pending",
        "requested_by": g.user_id,
    }), 201
