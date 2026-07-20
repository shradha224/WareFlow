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
        # 1. Average Batch Completion Time
        cur.execute("""
            SELECT AVG(TIMESTAMPDIFF(SECOND, pb.created_at, qc.checking_date) / 3600.0) AS avg_hours
            FROM Production_Batches pb
            JOIN Finished_Goods fg ON pb.batch_id = fg.batch_id
            JOIN Quality_Check qc ON fg.finished_good_id = qc.finished_good_id
            WHERE fg.qc_status = 'Passed'
              AND qc.inspection_type = 'Finished Good'
              AND qc.result = 'Pass'
        """)
        row_completion = cur.fetchone()
        avg_completion_hours = float(row_completion["avg_hours"]) if row_completion and row_completion["avg_hours"] is not None else 0.0

        # 2. Average Stage Transition Time
        cur.execute("""
            SELECT AVG(TIMESTAMPDIFF(SECOND, start_timestamp, end_timestamp) / 3600.0) AS avg_hours
            FROM Batch_Stages
            WHERE status = 'Complete'
              AND start_timestamp IS NOT NULL
              AND end_timestamp IS NOT NULL
              AND stage_id NOT IN (
                  SELECT MIN(stage_id)
                  FROM Batch_Stages
                  GROUP BY batch_id
              )
        """)
        row_transition = cur.fetchone()
        avg_transition_hours = float(row_transition["avg_hours"]) if row_transition and row_transition["avg_hours"] is not None else 0.0

        # 3. Average Final QC Time
        cur.execute("""
            SELECT AVG(TIMESTAMPDIFF(SECOND, start_timestamp, end_timestamp) / 3600.0) AS avg_hours
            FROM Batch_Stages
            WHERE status = 'Complete'
              AND start_timestamp IS NOT NULL
              AND end_timestamp IS NOT NULL
              AND stage_id IN (
                  SELECT MAX(stage_id)
                  FROM Batch_Stages
                  GROUP BY batch_id
              )
        """)
        row_qc = cur.fetchone()
        avg_qc_hours = float(row_qc["avg_hours"]) if row_qc and row_qc["avg_hours"] is not None else 0.0

        # Populate stage_metrics expecting assembly, production, and qc
        stage_metrics = [
            {"stage_name": "Assembly", "avg_elapsed": round(avg_completion_hours, 2), "target_hours": 0.0},
            {"stage_name": "Production", "avg_elapsed": round(avg_transition_hours, 2), "target_hours": 0.0},
            {"stage_name": "QC", "avg_elapsed": round(avg_qc_hours, 2), "target_hours": 0.0}
        ]

        # 4. Production Completed Analytics Count (QC Result = PASS)
        cur.execute("""
            SELECT COALESCE(SUM(pb.target_qty), 0) AS completed_count
            FROM Production_Batches pb
            JOIN Finished_Goods fg ON pb.batch_id = fg.batch_id
            JOIN Quality_Check qc ON fg.finished_good_id = qc.finished_good_id
            WHERE fg.qc_status = 'Passed'
              AND qc.inspection_type = 'Finished Good'
              AND qc.result = 'Pass'
        """)
        production_completed_count = int(cur.fetchone()["completed_count"])

        # 5. Delay Detection logs batch-by-batch (Actual > Target)
        cur.execute("""
            SELECT 
                bs.stage_name, 
                bs.batch_id,
                bs.target_hours, 
                bs.start_timestamp, 
                bs.end_timestamp
            FROM Batch_Stages bs
            WHERE bs.end_timestamp IS NOT NULL AND bs.start_timestamp IS NOT NULL
            ORDER BY bs.end_timestamp DESC
        """)
        completed_stages = cur.fetchall()
        
        delay_logs = []
        for stage in completed_stages:
            actual_time_seconds = (stage["end_timestamp"] - stage["start_timestamp"]).total_seconds()
            actual_time_hours = max(0.0, actual_time_seconds / 3600.0)
            target_hours = float(stage["target_hours"])
            delay = actual_time_hours - target_hours
            
            if delay > 0.0:
                delay_display = f"+{delay:.2f} hrs"
                delay_logs.append({
                    "stage_name": f"{stage['stage_name']} ({stage['batch_id']})",
                    "actual_time_elapsed": f"{actual_time_hours:.2f} hrs",
                    "target_time": f"{target_hours:.2f} hrs",
                    "delay_display": delay_display
                })

        # 6. Average QC pass rate for Raw Materials only
        cur.execute("""
            SELECT
                COALESCE(SUM(CASE WHEN result = 'Pass' THEN 1 ELSE 0 END), 0) AS passed,
                COALESCE(SUM(CASE WHEN result = 'Fail' THEN 1 ELSE 0 END), 0) AS failed,
                COUNT(*) AS total
            FROM Quality_Check
            WHERE inspection_type = 'Raw Material'
        """)
        rm_row = cur.fetchone()
        rm_passed = int(rm_row["passed"])
        rm_failed = int(rm_row["failed"])
        rm_total = int(rm_row["total"])
        rm_pass_rate = round(rm_passed / rm_total * 100, 2) if rm_total > 0 else 0.0

        # Finished Goods QC metrics
        cur.execute("""
            SELECT
                COALESCE(SUM(CASE WHEN result = 'Pass' THEN 1 ELSE 0 END), 0) AS passed,
                COALESCE(SUM(CASE WHEN result = 'Fail' THEN 1 ELSE 0 END), 0) AS failed,
                COUNT(*) AS total
            FROM Quality_Check
            WHERE inspection_type = 'Finished Good'
        """)
        fg_row = cur.fetchone()
        fg_passed = int(fg_row["passed"])
        fg_failed = int(fg_row["failed"])
        fg_total = int(fg_row["total"])
        fg_pass_rate = round(fg_passed / fg_total * 100, 2) if fg_total > 0 else 0.0

        # 7. Average delay (hours) across completed stages
        cur.execute("""
            SELECT AVG(delayed_by) AS avg_delay
            FROM Batch_Stages
            WHERE status = 'Complete'
        """)
        row_delay = cur.fetchone()
        avg_delay_hours = float(row_delay["avg_delay"]) if row_delay and row_delay["avg_delay"] is not None else 0.0

        # Recent activity logs
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
                (SELECT 'Quality Inspection', inspection_id, result, checking_date
                  FROM Quality_Check)
                UNION ALL
                (SELECT 'Material Transfer', transfer_id, transfer_status, dispatched_at
                  FROM Material_Transfers)
            ) AS combined_logs
            ORDER BY event_time DESC
            LIMIT %s
        """, (log_limit,))
        logs = cur.fetchall()

    return jsonify({
        "average_batch_completion_hours": round(avg_completion_hours, 2),
        "average_stage_transition_hours": round(avg_transition_hours, 2),
        "average_final_qc_hours": round(avg_qc_hours, 2),
        "averages": {
            "avg_delay_hours": round(avg_delay_hours, 2),
            "avg_completion_hours": round(avg_completion_hours, 2),
            "avg_qc_pass_rate_percent": rm_pass_rate,
        },
        "raw_material_qc": {
            "passed": rm_passed,
            "failed": rm_failed,
            "pass_rate": rm_pass_rate
        },
        "finished_goods_qc": {
            "passed": fg_passed,
            "failed": fg_failed,
            "pass_rate": fg_pass_rate
        },
        "stage_metrics": stage_metrics,
        "production_completed_count": production_completed_count,
        "delay_logs": delay_logs,
        "logs": logs
    }), 200