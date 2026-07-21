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
    STAGE_ORDER = ["Assembly", "QC", "Packaging", "Dispatch"]
    try:
        idx = STAGE_ORDER.index(current_stage)
    except ValueError:
        try:
            idx = [s.lower() for s in STAGE_ORDER].index(current_stage.lower())
        except ValueError:
            return None
    if idx + 1 < len(STAGE_ORDER):
        return STAGE_ORDER[idx + 1]
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

    if not all([batch_id, component_id, stage_name]):
        return jsonify({"error": "batch_id, component_id, and stage_name are required"}), 400

    # Map frontend stage names like "Assembly Station", "Testing", "Quality Check", "Packaging" to DB stage names
    STAGE_NAME_MAP = {
        "assembly station": "Assembly",
        "assembly": "Assembly",
        "testing": "QC",
        "quality check": "QC",
        "qc": "QC",
        "quality": "QC",
        "packaging": "Packaging",
        "dispatch": "Dispatch"
    }

    with get_db_cursor(commit=True) as cur:
        # Check if the unmapped stage name exists for this batch
        cur.execute("SELECT 1 FROM batch_stages WHERE batch_id = %s AND stage_name = %s", (batch_id, stage_name))
        if cur.fetchone():
            db_stage_name = stage_name
        else:
            db_stage_name = STAGE_NAME_MAP.get(stage_name.lower(), stage_name)

    with get_db_cursor(commit=True) as cur:
        # Validate batch + component
        cur.execute("SELECT * FROM production_batches WHERE batch_id = %s FOR UPDATE", (batch_id,))
        batch = cur.fetchone()
        if not batch:
            return jsonify({"error": f"Unknown batch_id '{batch_id}'"}), 404

        # Check preceding stage completion
        cur.execute("SELECT stage_name, status FROM batch_stages WHERE batch_id = %s ORDER BY stage_id ASC", (batch_id,))
        stages_list = cur.fetchall()
        
        # Find index of db_stage_name
        stage_idx = -1
        for i, s in enumerate(stages_list):
            if s["stage_name"].lower() == db_stage_name.lower():
                stage_idx = i
                break
        
        if stage_idx > 0:
            prev_stage = stages_list[stage_idx - 1]
            if prev_stage["status"] != "Complete":
                return jsonify({
                    "error": f"Cannot log consumption for stage '{db_stage_name}' because preceding stage '{prev_stage['stage_name']}' is not complete for all components"
                }), 400

        # Look up qty_used if not provided
        if qty_used is None:
            cur.execute("""
                SELECT quantity_required
                FROM junction_of_materials
                WHERE product_id = %s AND component_id = %s
            """, (batch["product_id"], component_id))
            bom_row = cur.fetchone()
            if not bom_row:
                return jsonify({"error": f"Component '{component_id}' not mapped to product in Bill of Materials"}), 400
            qty_used = bom_row["quantity_required"] * units_completed

        # Check if already consumed in any stage for this batch
        cur.execute("""
            SELECT COUNT(*) AS cnt
            FROM component_consumption
            WHERE batch_id = %s AND component_id = %s
        """, (batch_id, component_id))
        already_consumed = cur.fetchone()["cnt"] > 0

        if not already_consumed:
            cur.execute("SELECT floor_stock FROM components WHERE component_id = %s FOR UPDATE", (component_id,))
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
                UPDATE components SET floor_stock = floor_stock - %s
                WHERE component_id = %s
            """, (qty_used, component_id))

        # 2. Create consumption log
        cur.execute("""
            INSERT INTO component_consumption (batch_id, component_id, stage_name, qty_used, status)
            VALUES (%s, %s, %s, %s, 'Active')
        """, (batch_id, component_id, db_stage_name, qty_used))
        consumption_id = cur.lastrowid

        # 3. Determine target and completed quantities at component level
        cur.execute("""
            SELECT quantity_required
            FROM junction_of_materials
            WHERE product_id = %s AND component_id = %s
        """, (batch["product_id"], component_id))
        bom_row = cur.fetchone()
        if not bom_row:
            return jsonify({"error": f"Component '{component_id}' not mapped to product"}), 400
        qty_per_product = bom_row["quantity_required"]
        
        # Calculate component progress in this stage
        cur.execute("""
            SELECT SUM(qty_used) AS total
            FROM component_consumption
            WHERE batch_id = %s AND component_id = %s AND stage_name = %s
        """, (batch_id, component_id, db_stage_name))
        total_row = cur.fetchone()
        total_consumed = total_row["total"] or 0

        target_qty_for_comp = qty_per_product * batch["target_qty"]
        target_reached = total_consumed >= target_qty_for_comp
        
        stage_closure = None
        remaining_stages = []

        if target_reached:
            # System checks batch_stages for remaining stages, excluding QC stages
            cur.execute("SELECT stage_name, status, stage_id FROM batch_stages WHERE batch_id = %s ORDER BY stage_id ASC", (batch_id,))
            all_stages = cur.fetchall()
            
            is_qc_stage = lambda name: name.lower() in ("qc", "quality check", "quality", "final qc", "quality control")
            production_stages = [s for s in all_stages if not is_qc_stage(s["stage_name"])]
            qc_stages = [s for s in all_stages if is_qc_stage(s["stage_name"])]
            
            found_current = False
            for s in production_stages:
                if found_current:
                    remaining_stages.append(s["stage_name"])
                elif s["stage_name"].lower() == db_stage_name.lower():
                    found_current = True

            if not remaining_stages:
                # No remaining stages, so this is the final stage.
                # Check if all components have completed the final stage
                from completion_helper import is_batch_production_complete
                all_components_done = is_batch_production_complete(cur, batch_id)

                if all_components_done:
                    # Complete the final stage now.
                    cur.execute("""
                        SELECT * FROM batch_stages
                        WHERE batch_id = %s AND stage_name = %s
                        FOR UPDATE
                    """, (batch_id, db_stage_name))
                    stage = cur.fetchone()

                    if stage:
                        cur.execute("""
                            UPDATE batch_stages
                            SET end_timestamp = CURRENT_TIMESTAMP,
                                actual_hours = TIMESTAMPDIFF(MINUTE, COALESCE(start_timestamp, CURRENT_TIMESTAMP), CURRENT_TIMESTAMP) / 60,
                                status = 'Complete'
                            WHERE stage_id = %s
                        """, (stage["stage_id"],))

                        cur.execute("SELECT actual_hours, target_hours FROM batch_stages WHERE stage_id = %s", (stage["stage_id"],))
                        updated_stage = cur.fetchone()
                        actual_h = float(updated_stage["actual_hours"] or 0)
                        target_h = float(updated_stage["target_hours"] or 0)
                        delay_hours = max(0.0, actual_h - target_h)
                        cur.execute("""
                            UPDATE batch_stages SET delayed_by = %s WHERE stage_id = %s
                        """, (delay_hours, stage["stage_id"]))

                        stage_closure = {
                            "closed_stage": db_stage_name,
                            "elapsed_hours": actual_h,
                            "target_hours": target_h,
                            "is_delayed": bool(delay_hours > 0.0),
                            "next_stage": None,
                        }

                    # Start the next stage (Final QC) if present
                    if qc_stages:
                        final_qc_stage = qc_stages[0]
                        cur.execute("""
                            UPDATE batch_stages
                            SET start_timestamp = COALESCE(start_timestamp, CURRENT_TIMESTAMP),
                                status = 'In Progress'
                            WHERE stage_id = %s
                        """, (final_qc_stage["stage_id"],))

                    # Mark production batch status as Complete and set completed_qty to target_qty
                    cur.execute("""
                        UPDATE production_batches
                        SET status = 'Complete', completed_qty = target_qty
                        WHERE batch_id = %s
                    """, (batch_id,))

                    # Check and generate Finished Goods record if not exists
                    cur.execute("SELECT finished_good_id FROM finished_goods WHERE batch_id = %s", (batch_id,))
                    if not cur.fetchone():
                        import uuid
                        finished_good_id = f"FG-{uuid.uuid4().hex[:8].upper()}"
                        cur.execute("""
                            INSERT INTO finished_goods (finished_good_id, batch_id, product_id, qc_status)
                            VALUES (%s, %s, %s, 'Pending QC')
                        """, (finished_good_id, batch_id, batch["product_id"]))

    return jsonify({
        "message": "Component consumption recorded",
        "consumption_id": consumption_id,
        "batch_id": batch_id,
        "completed_qty": total_consumed,
        "target_qty": target_qty_for_comp,
        "target_reached": target_reached,
        "remaining_stages": remaining_stages,
        "stage_closure": stage_closure,
    }), 201


@component_consumption_bp.route("/api/consumption/components", methods=["GET"])
@login_required
def get_received_components():
    batch_id = request.args.get("batch_id")
    if not batch_id:
        return jsonify({"error": "batch_id is required"}), 400
    with get_db_cursor() as cur:
        cur.execute("SELECT product_id, target_qty FROM production_batches WHERE batch_id = %s", (batch_id,))
        batch = cur.fetchone()
        if not batch:
            return jsonify({"error": f"Unknown batch_id '{batch_id}'"}), 404
        
        # Get final production stage of this batch (excluding QC stages)
        cur.execute("""
            SELECT stage_name FROM batch_stages
            WHERE batch_id = %s
            ORDER BY stage_id ASC
        """, (batch_id,))
        all_stages = cur.fetchall()
        is_qc_stage = lambda name: name.lower() in ("qc", "quality check", "quality", "final qc", "quality control")
        production_stages = [s for s in all_stages if not is_qc_stage(s["stage_name"])]
        final_stage = production_stages[-1]["stage_name"] if production_stages else None

        cur.execute("""
            SELECT DISTINCT c.component_id, c.part_name, bom.quantity_required
            FROM components c
            JOIN junction_of_materials bom ON c.component_id = bom.component_id
            JOIN material_transfers mt ON mt.component_id = c.component_id
            WHERE bom.product_id = %s
              AND mt.transfer_status = 'Received'
              AND mt.batch_id = %s
            ORDER BY c.part_name ASC
        """, (batch["product_id"], batch_id))
        components = cur.fetchall()

        unfinished_components = []
        for comp in components:
            if final_stage:
                req_qty = comp["quantity_required"] * batch["target_qty"]
                cur.execute("""
                    SELECT SUM(qty_used) AS total
                    FROM component_consumption
                    WHERE batch_id = %s AND component_id = %s AND stage_name = %s
                """, (batch_id, comp["component_id"], final_stage))
                consumed = cur.fetchone()["total"] or 0
                if consumed >= req_qty:
                    continue
            unfinished_components.append({
                "component_id": comp["component_id"],
                "part_name": comp["part_name"]
            })

    return jsonify({"components": unfinished_components}), 200


@component_consumption_bp.route("/api/consumption/stages", methods=["GET"])
@login_required
def get_active_batch_stages():
    batch_id = request.args.get("batch_id")
    if not batch_id:
        return jsonify({"error": "batch_id is required"}), 400
    with get_db_cursor() as cur:
        cur.execute("""
            SELECT stage_name
            FROM batch_stages
            WHERE batch_id = %s
            ORDER BY stage_id ASC
        """, (batch_id,))
        stages = cur.fetchall()
        if len(stages) > 1:
            stages = stages[:-1]  # Exclude Final QC stage
    return jsonify({"stages": stages}), 200


@component_consumption_bp.route("/api/batches/<batch_id>/transition", methods=["POST"])
@login_required
@role_required("Worker", "Supervisor")
def transition_batch_stage(batch_id):
    data = request.get_json(silent=True) or {}
    current_stage = data.get("current_stage")
    next_stage = data.get("next_stage")

    if not current_stage or not next_stage:
        return jsonify({"error": "current_stage and next_stage are required"}), 400

    # Normalize stage names
    STAGE_NAME_MAP = {
        "assembly station": "Assembly",
        "assembly": "Assembly",
        "testing": "QC",
        "quality check": "QC",
        "qc": "QC",
        "quality": "QC",
        "packaging": "Packaging",
        "dispatch": "Dispatch"
    }

    with get_db_cursor(commit=True) as cur:
        # Check if the unmapped current stage name exists for this batch
        cur.execute("SELECT 1 FROM batch_stages WHERE batch_id = %s AND stage_name = %s", (batch_id, current_stage))
        if cur.fetchone():
            db_current_stage = current_stage
        else:
            db_current_stage = STAGE_NAME_MAP.get(current_stage.lower(), current_stage)

        # Check if the unmapped next stage name exists for this batch
        cur.execute("SELECT 1 FROM batch_stages WHERE batch_id = %s AND stage_name = %s", (batch_id, next_stage))
        if cur.fetchone():
            db_next_stage = next_stage
        else:
            db_next_stage = STAGE_NAME_MAP.get(next_stage.lower(), next_stage)

        # 1. Check if the current stage is completed for ALL components
        cur.execute("SELECT product_id, target_qty FROM production_batches WHERE batch_id = %s", (batch_id,))
        batch = cur.fetchone()
        product_id = batch["product_id"]
        target_qty = batch["target_qty"]

        cur.execute("SELECT component_id, quantity_required FROM junction_of_materials WHERE product_id = %s", (product_id,))
        bom_items = cur.fetchall()

        all_components_done = True
        for item in bom_items:
            comp_id = item["component_id"]
            req_qty = item["quantity_required"] * target_qty
            
            cur.execute("""
                SELECT SUM(qty_used) AS total_consumed
                FROM component_consumption
                WHERE batch_id = %s AND component_id = %s AND stage_name = %s
            """, (batch_id, comp_id, db_current_stage))
            cc_row = cur.fetchone()
            consumed = cc_row["total_consumed"] or 0
            if consumed < req_qty:
                all_components_done = False
                break

        # Only complete current_stage and start next_stage if all components are done with current_stage
        if all_components_done:
            # Complete the current stage
            cur.execute("""
                SELECT * FROM batch_stages
                WHERE batch_id = %s AND stage_name = %s
                FOR UPDATE
            """, (batch_id, db_current_stage))
            curr_stage_row = cur.fetchone()
            if curr_stage_row:
                cur.execute("""
                    UPDATE batch_stages
                    SET end_timestamp = CURRENT_TIMESTAMP,
                        actual_hours = TIMESTAMPDIFF(MINUTE, COALESCE(start_timestamp, CURRENT_TIMESTAMP), CURRENT_TIMESTAMP) / 60,
                        status = 'Complete'
                    WHERE stage_id = %s
                """, (curr_stage_row["stage_id"],))

                cur.execute("SELECT actual_hours, target_hours FROM batch_stages WHERE stage_id = %s", (curr_stage_row["stage_id"],))
                updated_stage = cur.fetchone()
                actual_h = float(updated_stage["actual_hours"] or 0)
                target_h = float(updated_stage["target_hours"] or 0)
                delay_hours = max(0.0, actual_h - target_h)
                cur.execute("""
                    UPDATE batch_stages SET delayed_by = %s WHERE stage_id = %s
                """, (delay_hours, curr_stage_row["stage_id"]))

            # Start the next stage
            cur.execute("""
                SELECT * FROM batch_stages
                WHERE batch_id = %s AND stage_name = %s
                FOR UPDATE
            """, (batch_id, db_next_stage))
            next_stage_row = cur.fetchone()
            if next_stage_row:
                if next_stage_row["status"] != "In Progress":
                    cur.execute("""
                        UPDATE batch_stages
                        SET start_timestamp = COALESCE(start_timestamp, CURRENT_TIMESTAMP),
                            status = 'In Progress'
                        WHERE stage_id = %s
                    """, (next_stage_row["stage_id"],))
            else:
                return jsonify({"error": f"Next stage '{next_stage}' not defined for this batch"}), 400

            message = f"Transitioned from {current_stage} to {next_stage}"
        else:
            message = f"Component completed {current_stage}. Waiting for other components to finish."

    return jsonify({
        "message": message,
        "batch_id": batch_id,
        "current_stage": current_stage,
        "next_stage": next_stage,
        "all_components_done": all_components_done
    }), 200
