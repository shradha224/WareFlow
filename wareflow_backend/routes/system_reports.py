"""
routes/system_reports.py
--------------------------
USED ON: System Reports page.

Endpoint:
  GET /api/reports
      -> Calculate averages (avg stage delay, avg batch completion time,
         avg QC pass rate) and retrieve recent activity logs.
"""

from flask import Blueprint, jsonify, request
from auth import login_required
from db import get_db_cursor

system_reports_bp = Blueprint("system_reports", __name__)


@system_reports_bp.route("/api/reports", methods=["GET"])
@login_required
def get_reports():
    log_limit = int(request.args.get("log_limit", 50))

    with get_db_cursor() as cur:
        # Average delay (hours) across completed stages
        cur.execute("""
            SELECT AVG(elapsed_hours - target_hours) AS avg_delay_hours
            FROM Batch_Stages
            WHERE end_timestamp IS NOT NULL
        """)
        avg_delay_hours = cur.fetchone()["avg_delay_hours"]

        # Average batch completion time (hours) from creation to completion
        cur.execute("""
            SELECT AVG(TIMESTAMPDIFF(HOUR, pb.created_at, fs.end_timestamp)) AS avg_completion_hours
            FROM Production_Batches pb
            JOIN Batch_Stages fs ON fs.batch_id = pb.batch_id
            WHERE pb.status = 'Complete' AND fs.end_timestamp IS NOT NULL
        """)
        avg_completion_hours = cur.fetchone()["avg_completion_hours"]

        # Average QC pass rate
        cur.execute("""
            SELECT
                SUM(CASE WHEN result = 'Pass' THEN 1 ELSE 0 END) AS passed,
                COUNT(*) AS total
            FROM Quality_Inspections
        """)
        qc_row = cur.fetchone()
        avg_qc_pass_rate = (
            round((qc_row["passed"] or 0) / qc_row["total"] * 100, 2)
            if qc_row["total"] else None
        )

        # Recent activity logs pulled from the most relevant tables, merged by time
        cur.execute("""
            SELECT log_type, ref_id, detail, event_time FROM (
                (SELECT 'Material Request' AS log_type, request_id AS ref_id,
                        status AS detail, created_at AS event_time
                 FROM Material_Requests)
                UNION ALL
                (SELECT 'Batch Stage', stage_id, CONCAT(stage_name, ' - ', status),
                        COALESCE(end_timestamp, start_timestamp)
                 FROM Batch_Stages)
                UNION ALL
                (SELECT 'Quality Inspection', inspection_id, result, inspection_date
                 FROM Quality_Inspections)
                UNION ALL
                (SELECT 'Material Transfer', transfer_id, transfer_status, dispatched_at
                 FROM Material_Transfers)
            ) AS combined_logs
            ORDER BY event_time DESC
            LIMIT %s
        """, (log_limit,))
        logs = cur.fetchall()

    return jsonify({
        "averages": {
            "avg_delay_hours": round(avg_delay_hours, 2) if avg_delay_hours is not None else None,
            "avg_completion_hours": round(avg_completion_hours, 2) if avg_completion_hours is not None else None,
            "avg_qc_pass_rate_percent": avg_qc_pass_rate,
        },
        "logs": logs,
    }), 200
