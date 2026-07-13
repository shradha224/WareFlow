"""
routes/component_consumption.py
----------------------------------
USED ON: Component Consumption page.

Endpoint:
  POST /api/consumption
       { batch_id, component_id, stage_name, qty_used, units_completed? }
       -> Reduce floor stock, create a consumption log, increment the
          batch's completed quantity.

          If the batch's target quantity is reached as a result of this
          call:
            -> Store the current stage's end timestamp, calculate delay,
               and move the batch to the next stage (per config.STAGE_ORDER).
"""

from flask import Blueprint, request, jsonify
from auth import login_required, role_required
from db import get_db_cursor
from config import Config

component_consumption_bp = Blueprint("component_consumption", __name__)


def _next_stage_name(current_stage: str):
    try:
        idx = Config.STAGE_ORDER.index(current_stage)
    except ValueError:
        return None
    if idx + 1 < len(Config.STAGE_ORDER):
        return Config.STAGE_ORDER[idx + 1]
    return None


@component_consumption_bp.route("/api/consumption", methods=["POST"])
@login_required
@role_required("Worker", "Supervisor")
def mark_consumption_complete():
    data = request.get_json(silent=True) or {}
    batch_id = data.get("batch_id")
    component_id = data.get("component_id")
    stage_name = data.get("stage_name")
    qty_used = data.get("qty_used")
    units_completed = data.get("units_completed", 1)

    if not all([batch_id, component_id, stage_name, qty_used]):
        return jsonify({"error": "batch_id, component_id, stage_name, and qty_used are required"}), 400

    with get_db_cursor(commit=True) as cur:
        # Validate batch + component
        cur.execute("SELECT * FROM Production_Batches WHERE batch_id = %s FOR UPDATE", (batch_id,))
        batch = cur.fetchone()
        if not batch:
            return jsonify({"error": f"Unknown batch_id '{batch_id}'"}), 404

        cur.execute("SELECT floor_stock FROM Components WHERE component_id = %s FOR UPDATE", (component_id,))
        comp = cur.fetchone()
        if not comp:
            return jsonify({"error": f"Unknown component_id '{component_id}'"}), 404
        if comp["floor_stock"] < qty_used:
            return jsonify({
                "error": "Insufficient floor stock for this component",
                "available": comp["floor_stock"],
                "requested": qty_used,
            }), 409

        # 1. Reduce floor stock
        cur.execute("""
            UPDATE Components SET floor_stock = floor_stock - %s
            WHERE component_id = %s
        """, (qty_used, component_id))

        # 2. Create consumption log
        cur.execute("""
            INSERT INTO Component_Consumption (component_id, stage_name, qty_used, status)
            VALUES (%s, %s, %s, 'Active')
        """, (component_id, stage_name, qty_used))
        consumption_id = cur.lastrowid

        # 3. Increment batch completed quantity
        new_completed_qty = batch["completed_qty"] + units_completed
        cur.execute("""
            UPDATE Production_Batches SET completed_qty = %s WHERE batch_id = %s
        """, (new_completed_qty, batch_id))

        stage_closure = None
        target_reached = new_completed_qty >= batch["target_qty"]

        if target_reached:
            # Ensure the current stage has a start_timestamp to measure against
            cur.execute("""
                SELECT * FROM Batch_Stages
                WHERE batch_id = %s AND stage_name = %s
                FOR UPDATE
            """, (batch_id, stage_name))
            stage = cur.fetchone()

            if stage:
                # Calculate elapsed hours and delay
                cur.execute("""
                    UPDATE Batch_Stages
                    SET end_timestamp = CURRENT_TIMESTAMP,
                        elapsed_hours = TIMESTAMPDIFF(MINUTE, COALESCE(start_timestamp, CURRENT_TIMESTAMP), CURRENT_TIMESTAMP) / 60,
                        status = 'Complete'
                    WHERE stage_id = %s
                """, (stage["stage_id"],))

                cur.execute("SELECT elapsed_hours, target_hours FROM Batch_Stages WHERE stage_id = %s", (stage["stage_id"],))
                updated_stage = cur.fetchone()
                is_delayed = updated_stage["elapsed_hours"] > updated_stage["target_hours"]
                cur.execute("""
                    UPDATE Batch_Stages SET is_delayed = %s WHERE stage_id = %s
                """, (is_delayed, stage["stage_id"]))

                # Move batch to the next stage, if one exists
                next_stage = _next_stage_name(stage_name)
                if next_stage:
                    cur.execute("""
                        SELECT stage_id FROM Batch_Stages
                        WHERE batch_id = %s AND stage_name = %s
                    """, (batch_id, next_stage))
                    next_stage_row = cur.fetchone()
                    if next_stage_row:
                        cur.execute("""
                            UPDATE Batch_Stages
                            SET start_timestamp = CURRENT_TIMESTAMP, status = 'In Progress'
                            WHERE stage_id = %s
                        """, (next_stage_row["stage_id"],))

                stage_closure = {
                    "closed_stage": stage_name,
                    "elapsed_hours": float(updated_stage["elapsed_hours"]),
                    "target_hours": float(updated_stage["target_hours"]),
                    "is_delayed": bool(is_delayed),
                    "next_stage": next_stage,
                }

    return jsonify({
        "message": "Component consumption recorded",
        "consumption_id": consumption_id,
        "batch_id": batch_id,
        "completed_qty": new_completed_qty,
        "target_qty": batch["target_qty"],
        "target_reached": target_reached,
        "stage_closure": stage_closure,
    }), 201
