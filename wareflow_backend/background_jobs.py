"""
background_jobs.py
--------------------
USED FOR: Background System Processes (run on a schedule via scheduler.py,
or triggered manually through the /api/jobs/run/<job_name> routes for
testing/ops).

Implements the 5 rows of the "Background System Processes" table:
  1. low_stock_detection      - Check inventory against threshold, create alerts
  2. delay_detection          - Compare actual stage duration with target duration
  3. batch_completion         - completed_qty == target_qty -> status = Complete
  4. finished_good_generation - Generate Finished Good ID, move item to QC
  5. demand_prediction        - Analyze historical data, generate forecast
"""

import uuid
import datetime
import statistics
from db import get_db_cursor


# ---------------------------------------------------------------------------
# 1. Low Stock Detection
# ---------------------------------------------------------------------------
def low_stock_detection():
    """
    Checks every component's total stock against its min_threshold.
    The schema has no dedicated Alerts table, so an "alert" here means:
    a low-stock component that does NOT already have a Pending material
    request open. For each such component we auto-create one Pending
    Material_Request (mirrors the Supervisor Dashboard's 'Place Order' action)
    and return the full list of components currently below threshold.
    """
    alerts_created = []
    with get_db_cursor(commit=True) as cur:
        cur.execute("""
            SELECT component_id, part_name, warehouse_stock, floor_stock, min_threshold
            FROM Components
            WHERE (warehouse_stock + floor_stock) < min_threshold
        """)
        low_stock_components = cur.fetchall()

        for comp in low_stock_components:
            cur.execute("""
                SELECT request_id FROM Material_Requests
                WHERE component_id = %s AND status = 'Pending'
            """, (comp["component_id"],))
            if cur.fetchone():
                continue  # already has an open request, don't duplicate the alert

            shortfall = comp["min_threshold"] - (comp["warehouse_stock"] + comp["floor_stock"])
            cur.execute("""
                INSERT INTO Material_Requests (component_id, requested_qty, status)
                VALUES (%s, %s, 'Pending')
            """, (comp["component_id"], shortfall))
            alerts_created.append({
                "component_id": comp["component_id"],
                "part_name": comp["part_name"],
                "auto_requested_qty": shortfall,
                "request_id": cur.lastrowid,
            })

    return {
        "low_stock_components": low_stock_components,
        "alerts_created": alerts_created,
    }


# ---------------------------------------------------------------------------
# 2. Delay Detection
# ---------------------------------------------------------------------------
def delay_detection():
    """
    For every stage currently in progress (has a start_timestamp, no
    end_timestamp yet), compares elapsed time so far against target_hours
    and flags is_delayed when it's overrun.
    """
    flagged = []
    with get_db_cursor(commit=True) as cur:
        cur.execute("""
            SELECT stage_id, batch_id, stage_name, target_hours, start_timestamp
            FROM Batch_Stages
            WHERE start_timestamp IS NOT NULL AND end_timestamp IS NULL
        """)
        in_progress_stages = cur.fetchall()

        now = datetime.datetime.utcnow()
        for stage in in_progress_stages:
            elapsed_hours = (now - stage["start_timestamp"]).total_seconds() / 3600.0
            is_delayed = elapsed_hours > float(stage["target_hours"])

            cur.execute("""
                UPDATE Batch_Stages
                SET elapsed_hours = %s, is_delayed = %s
                WHERE stage_id = %s
            """, (round(elapsed_hours, 2), is_delayed, stage["stage_id"]))

            if is_delayed:
                flagged.append({
                    "stage_id": stage["stage_id"],
                    "batch_id": stage["batch_id"],
                    "stage_name": stage["stage_name"],
                    "elapsed_hours": round(elapsed_hours, 2),
                    "target_hours": float(stage["target_hours"]),
                })

    return {"checked": len(in_progress_stages), "delayed": flagged}


# ---------------------------------------------------------------------------
# 3. Batch Completion
# ---------------------------------------------------------------------------
def batch_completion():
    """
    Any batch whose completed_qty has reached (or passed) target_qty and
    isn't already marked Complete gets its status flipped to 'Complete'.
    """
    completed_batches = []
    with get_db_cursor(commit=True) as cur:
        cur.execute("""
            SELECT batch_id, product_name, target_qty, completed_qty
            FROM Production_Batches
            WHERE completed_qty >= target_qty AND status != 'Complete'
        """)
        candidates = cur.fetchall()

        for batch in candidates:
            cur.execute("""
                UPDATE Production_Batches SET status = 'Complete' WHERE batch_id = %s
            """, (batch["batch_id"],))
            completed_batches.append(batch)

    return {"completed_batches": completed_batches}


# ---------------------------------------------------------------------------
# 4. Finished Good Generation
# ---------------------------------------------------------------------------
def _generate_finished_good_id() -> str:
    return f"FG-{uuid.uuid4().hex[:8].upper()}"


def finished_good_generation():
    """
    For batches that are Complete but don't yet have a Finished_Goods
    record, generates a Finished Good ID and moves the item into QC
    (qc_status = 'Pending QC'). Intended to run right after
    batch_completion() in the same job cycle.
    """
    generated = []
    with get_db_cursor(commit=True) as cur:
        cur.execute("""
            SELECT pb.batch_id, pb.product_name
            FROM Production_Batches pb
            LEFT JOIN Finished_Goods fg ON fg.batch_id = pb.batch_id
            WHERE pb.status = 'Complete' AND fg.finished_good_id IS NULL
        """)
        batches_needing_fg = cur.fetchall()

        for batch in batches_needing_fg:
            finished_good_id = _generate_finished_good_id()
            cur.execute("""
                INSERT INTO Finished_Goods (finished_good_id, batch_id, qc_status)
                VALUES (%s, %s, 'Pending QC')
            """, (finished_good_id, batch["batch_id"]))
            generated.append({
                "finished_good_id": finished_good_id,
                "batch_id": batch["batch_id"],
                "product_name": batch["product_name"],
                "qc_status": "Pending QC",
            })

    return {"generated": generated}


# ---------------------------------------------------------------------------
# 5. Demand Prediction
# ---------------------------------------------------------------------------
def demand_prediction(lookback_days: int = 30, forecast_days: int = 30):
    """
    For each component, looks at consumption over the trailing
    `lookback_days` and projects a simple forecast (average daily usage *
    forecast_days) for the next `forecast_days` window. This is a
    lightweight moving-average model; swap in a real forecasting library
    if higher accuracy is needed.
    """
    forecasts = []
    with get_db_cursor(commit=True) as cur:
        cur.execute("""
            SELECT component_id, DATE(consumed_at) AS usage_date, SUM(qty_used) AS daily_qty
            FROM Component_Consumption
            WHERE consumed_at >= (CURRENT_DATE - INTERVAL %s DAY)
            GROUP BY component_id, DATE(consumed_at)
        """, (lookback_days,))
        rows = cur.fetchall()

        usage_by_component = {}
        for row in rows:
            usage_by_component.setdefault(row["component_id"], []).append(row["daily_qty"])

        today = datetime.date.today()
        period_end = today + datetime.timedelta(days=forecast_days)

        for component_id, daily_quantities in usage_by_component.items():
            avg_daily_usage = statistics.mean(daily_quantities)
            predicted_demand_qty = round(avg_daily_usage * forecast_days)

            cur.execute("""
                INSERT INTO Demand_Forecasts
                    (component_id, predicted_demand_qty, forecast_period_start, forecast_period_end)
                VALUES (%s, %s, %s, %s)
            """, (component_id, predicted_demand_qty, today, period_end))

            forecasts.append({
                "component_id": component_id,
                "predicted_demand_qty": predicted_demand_qty,
                "forecast_period_start": str(today),
                "forecast_period_end": str(period_end),
            })

    return {"forecasts": forecasts}


# ---------------------------------------------------------------------------
# Convenience: run everything in the sensible dependency order
# ---------------------------------------------------------------------------
JOB_REGISTRY = {
    "low_stock_detection": low_stock_detection,
    "delay_detection": delay_detection,
    "batch_completion": batch_completion,
    "finished_good_generation": finished_good_generation,
    "demand_prediction": demand_prediction,
}


def run_all_jobs():
    results = {}
    for name in ["low_stock_detection", "delay_detection", "batch_completion",
                 "finished_good_generation", "demand_prediction"]:
        results[name] = JOB_REGISTRY[name]()
    return results
