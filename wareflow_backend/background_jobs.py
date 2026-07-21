
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
            FROM components
            WHERE (warehouse_stock + floor_stock) < min_threshold
        """)
        low_stock_components = cur.fetchall()

        for comp in low_stock_components:
            cur.execute("""
                SELECT request_id FROM material_requests
                WHERE component_id = %s AND status = 'Pending'
            """, (comp["component_id"],))
            if cur.fetchone():
                continue  # already has an open request, don't duplicate the alert

            shortfall = comp["min_threshold"] - (comp["warehouse_stock"] + comp["floor_stock"])
            cur.execute("""
                INSERT INTO material_requests (component_id, requested_qty, status)
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
            SELECT stage_id, batch_id, stage_name, target_hours, start_timestamp,
                   TIMESTAMPDIFF(SECOND, start_timestamp, NOW()) / 3600.0 AS elapsed_hours
            FROM batch_stages
            WHERE start_timestamp IS NOT NULL AND end_timestamp IS NULL
        """)
        in_progress_stages = cur.fetchall()

        for stage in in_progress_stages:
            elapsed_hours = max(0.0, float(stage["elapsed_hours"]))
            target_hours = float(stage["target_hours"] or 0.0)
            delay_hours = max(0.0, elapsed_hours - target_hours)

            cur.execute("""
                UPDATE batch_stages
                SET actual_hours = %s, delayed_by = %s
                WHERE stage_id = %s
            """, (round(elapsed_hours, 2), delay_hours, stage["stage_id"]))

            if delay_hours > 0.0:
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
            SELECT pb.batch_id, p.product_name, pb.target_qty, pb.completed_qty
            FROM production_batches pb
            JOIN products p ON pb.product_id = p.product_id
            WHERE pb.completed_qty >= pb.target_qty AND pb.status != 'Complete'
        """)
        candidates = cur.fetchall()

        for batch in candidates:
            cur.execute("""
                UPDATE production_batches SET status = 'Complete' WHERE batch_id = %s
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
    For batches that are Complete but don't yet have a finished_goods
    record, generates a Finished Good ID and moves the item into QC
    (qc_status = 'Pending QC'). Intended to run right after
    batch_completion() in the same job cycle.
    """
    generated = []
    with get_db_cursor(commit=True) as cur:
        cur.execute("""
            SELECT pb.batch_id, p.product_name, pb.product_id
            FROM production_batches pb
            JOIN products p ON pb.product_id = p.product_id
            LEFT JOIN finished_goods fg ON fg.batch_id = pb.batch_id
            WHERE pb.status = 'Complete' AND fg.finished_good_id IS NULL
        """)
        batches_needing_fg = cur.fetchall()

        for batch in batches_needing_fg:
            batch_id = batch["batch_id"]
            
            from completion_helper import is_batch_production_complete
            if not is_batch_production_complete(cur, batch_id):
                continue

            finished_good_id = _generate_finished_good_id()
            cur.execute("""
                INSERT INTO finished_goods (finished_good_id, batch_id, product_id, qc_status)
                VALUES (%s, %s, %s, 'Pending QC')
            """, (finished_good_id, batch_id, batch["product_id"]))
            generated.append({
                "finished_good_id": finished_good_id,
                "batch_id": batch_id,
                "product_name": batch["product_name"],
                "qc_status": "Pending QC",
            })

    return {"generated": generated}


# ---------------------------------------------------------------------------
# 5. Demand Prediction
# ---------------------------------------------------------------------------
def demand_prediction(lookback_days: int = 30, forecast_days: int = 7):
    """
    For each component, looks at consumption over the trailing
    `lookback_days` and projects a simple forecast (average daily usage *
    forecast_days) for the next `forecast_days` window. This is a
    lightweight moving-average model; swap in a real forecasting library
    if higher accuracy is needed.
    """
    forecasts = []
    with get_db_cursor(commit=True) as cur:
        # Clear old predictions
        cur.execute("DELETE FROM demand_predictions")

        cur.execute("""
            SELECT pb.product_id, DATE(fg.generation_date) AS completion_date, SUM(pb.completed_qty) AS daily_qty
            FROM finished_goods fg
            JOIN production_batches pb ON fg.batch_id = pb.batch_id
            WHERE fg.generation_date >= (CURRENT_DATE - INTERVAL %s DAY)
            GROUP BY pb.product_id, DATE(fg.generation_date)
        """, (lookback_days,))
        rows = cur.fetchall()

        usage_by_product = {}
        for row in rows:
            usage_by_product.setdefault(row["product_id"], []).append(row["daily_qty"])

        # Fetch all products to ensure every product gets predicted
        cur.execute("SELECT product_id FROM products")
        all_products = [p["product_id"] for p in cur.fetchall()]

        today = datetime.date.today()
        period_end = today + datetime.timedelta(days=forecast_days)

        for product_id in all_products:
            if product_id in usage_by_product:
                daily_quantities = usage_by_product[product_id]
                avg_daily_usage = statistics.mean(daily_quantities) if daily_quantities else 0.0
                predicted_demand_qty = round(avg_daily_usage * forecast_days)
            else:
                # Use fallback heuristic: BOM total * 10
                cur.execute("""
                    SELECT COALESCE(SUM(quantity_required), 0) AS total_bom
                    FROM junction_of_materials
                    WHERE product_id = %s
                """, (product_id,))
                total_bom = cur.fetchone()["total_bom"] or 0
                predicted_demand_qty = int(total_bom * 10)

            cur.execute("""
                INSERT INTO demand_predictions
                    (product_id, predicted_demand_qty, forecast_period_start, forecast_period_end)
                VALUES (%s, %s, %s, %s)
            """, (product_id, predicted_demand_qty, today, period_end))

            forecasts.append({
                "product_id": product_id,
                "predicted_demand_qty": predicted_demand_qty,
                "forecast_period_start": str(today),
                "forecast_period_end": str(period_end),
            })

    return {"forecasts": forecasts}


def cleanup_expired_otps():
    """
    Background job to delete expired OTP records from email_verification table.
    """
    deleted_count = 0
    with get_db_cursor(commit=True) as cur:
        cur.execute("DELETE FROM email_verification WHERE expiry_time < NOW()")
        deleted_count = cur.rowcount
    return {"deleted_expired_otps_count": deleted_count}


# ---------------------------------------------------------------------------
# Convenience: run everything in the sensible dependency order
# ---------------------------------------------------------------------------
JOB_REGISTRY = {
    "low_stock_detection": low_stock_detection,
    "delay_detection": delay_detection,
    "batch_completion": batch_completion,
    "finished_good_generation": finished_good_generation,
    "demand_prediction": demand_prediction,
    "cleanup_expired_otps": cleanup_expired_otps,
}



def run_all_jobs():
    results = {}
    for name in ["low_stock_detection", "delay_detection", "batch_completion",
                 "finished_good_generation", "demand_prediction"]:
        results[name] = JOB_REGISTRY[name]()
    return results
