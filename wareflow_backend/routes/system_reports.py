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
        # 1. Average Batch Completion Time (avoiding duplicate QC count)
        cur.execute("""
            SELECT AVG(TIMESTAMPDIFF(SECOND, pb.created_at, qc.checking_date) / 3600.0) AS avg_hours
            FROM production_batches pb
            JOIN finished_goods fg ON pb.batch_id = fg.batch_id
            JOIN (
                SELECT finished_good_id, MIN(checking_date) AS checking_date
                FROM quality_check
                WHERE inspection_type = 'Finished Good' AND result = 'Pass'
                GROUP BY finished_good_id
            ) qc ON fg.finished_good_id = qc.finished_good_id
            WHERE fg.qc_status = 'Passed'
        """)
        row_completion = cur.fetchone()
        avg_completion_hours = float(row_completion["avg_hours"]) if row_completion and row_completion["avg_hours"] is not None else 0.0

        # Fetch all completed stages to compute transition/QC/delay metrics in Python
        cur.execute("""
            SELECT 
                bs.stage_id,
                bs.stage_name, 
                bs.batch_id,
                bs.target_hours, 
                bs.start_timestamp, 
                bs.end_timestamp,
                pb.created_at AS batch_created_at
            FROM batch_stages bs
            JOIN production_batches pb ON bs.batch_id = pb.batch_id
            WHERE bs.status = 'Complete'
            ORDER BY bs.stage_id ASC
        """)
        all_completed_stages = cur.fetchall()

        # Group stages by batch to identify min and max stage_ids and calculate actual start timestamps
        batch_stages_map = {}
        for stage in all_completed_stages:
            bid = stage["batch_id"]
            if bid not in batch_stages_map:
                batch_stages_map[bid] = []
            batch_stages_map[bid].append(stage)

        transition_hours_list = []
        qc_hours_list = []
        all_delays_list = []
        delay_logs = []

        for bid, stages in batch_stages_map.items():
            min_id = stages[0]["stage_id"]
            max_id = stages[-1]["stage_id"]

            for idx, stage in enumerate(stages):
                start = stage["start_timestamp"]
                end = stage["end_timestamp"]

                if not start:
                    if idx > 0:
                        start = stages[idx-1]["end_timestamp"]
                    if not start:
                        start = stage["batch_created_at"]

                if not end:
                    continue
                if not start:
                    start = end

                actual_hours = max(0.0, (end - start).total_seconds() / 3600.0)
                target_hours = float(stage["target_hours"])
                delay = actual_hours - target_hours

                all_delays_list.append(max(0.0, delay))

                if stage["stage_id"] == max_id:
                    qc_hours_list.append(actual_hours)
                
                if stage["stage_id"] != min_id:
                    transition_hours_list.append(actual_hours)

                if delay > 0.0:
                    delay_display = f"+{delay:.2f} hrs"
                    delay_logs.append({
                        "stage_name": f"{stage['stage_name']} ({bid})",
                        "actual_time_elapsed": f"{actual_hours:.2f} hrs",
                        "target_time": f"{target_hours:.2f} hrs",
                        "delay_display": delay_display,
                        "end_timestamp": end
                    })

        # Sort delay logs by end_timestamp DESC
        delay_logs.sort(key=lambda x: x["end_timestamp"], reverse=True)
        for log in delay_logs:
            log.pop("end_timestamp", None)

        avg_transition_hours = sum(transition_hours_list) / len(transition_hours_list) if transition_hours_list else 0.0
        avg_qc_hours = sum(qc_hours_list) / len(qc_hours_list) if qc_hours_list else 0.0
        avg_delay_hours = sum(all_delays_list) / len(all_delays_list) if all_delays_list else 0.0

        # Populate stage_metrics expecting assembly, production, and qc
        stage_metrics = [
            {"stage_name": "Assembly", "avg_elapsed": round(avg_completion_hours, 2), "target_hours": 0.0},
            {"stage_name": "Production", "avg_elapsed": round(avg_transition_hours, 2), "target_hours": 0.0},
            {"stage_name": "QC", "avg_elapsed": round(avg_qc_hours, 2), "target_hours": 0.0}
        ]

        # 4. Production Completed Analytics Count (QC Result = PASS) using Finished Goods as single source of truth
        cur.execute("""
            SELECT COALESCE(SUM(pb.completed_qty), 0) AS completed_count
            FROM finished_goods fg
            JOIN production_batches pb ON fg.batch_id = pb.batch_id
            WHERE fg.qc_status = 'Passed'
        """)
        production_completed_count = int(cur.fetchone()["completed_count"])

        # 6. Average QC pass rate for Raw Materials only
        cur.execute("""
            SELECT
                COALESCE(SUM(CASE WHEN result = 'Pass' THEN 1 ELSE 0 END), 0) AS passed,
                COALESCE(SUM(CASE WHEN result = 'Fail' THEN 1 ELSE 0 END), 0) AS failed,
                COUNT(*) AS total
            FROM quality_check
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
            FROM quality_check
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
            FROM batch_stages
            WHERE status = 'Complete'
        """)
        row_delay = cur.fetchone()
        avg_delay_hours = float(row_delay["avg_delay"]) if row_delay and row_delay["avg_delay"] is not None else 0.0

        # Recent activity logs
        cur.execute("""
            SELECT log_type, ref_id, detail, event_time FROM (
                (SELECT 'Material Request' AS log_type, request_id AS ref_id,
                        status AS detail, created_at AS event_time
                  FROM material_requests)
                UNION ALL
                (SELECT 'Batch Stage', stage_id, CONCAT(stage_name, ' - ', status),
                        COALESCE(end_timestamp, start_timestamp)
                  FROM batch_stages)
                UNION ALL
                (SELECT 'Quality Inspection', inspection_id, result, checking_date
                  FROM quality_check)
                UNION ALL
                (SELECT 'Material Transfer', transfer_id, transfer_status, dispatched_at
                  FROM material_transfers)
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