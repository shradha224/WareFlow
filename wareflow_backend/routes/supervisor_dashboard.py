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
            FROM components
            WHERE (warehouse_stock + floor_stock) < min_threshold
        """)
        low_stock_alerts = cur.fetchall()

        # Pending material requests
        cur.execute("SELECT COUNT(*) AS pending_count FROM material_requests WHERE status = 'Pending'")
        pending_requests = cur.fetchone()["pending_count"]

        # Finished Goods QC only
        cur.execute("""
            SELECT
                SUM(CASE WHEN result = 'Pass' THEN 1 ELSE 0 END) AS passed,
                COUNT(*) AS total
            FROM quality_check
            WHERE inspection_type = 'Finished Good'
        """)
        qc_row = cur.fetchone()
        qc_pass_percentage = (
            round((qc_row["passed"] or 0) / qc_row["total"] * 100, 2)
            if qc_row and qc_row["total"] > 0 else 0.0
        )
        qc_fail_percentage = (
            round(100 - qc_pass_percentage, 2)
        )

        # Batch progress: completed_qty vs target_qty for active batches
        cur.execute("""
            SELECT pb.batch_id, p.product_name, pb.product_id, pb.target_qty, pb.completed_qty, pb.status
            FROM production_batches pb
            JOIN products p ON pb.product_id = p.product_id
            WHERE pb.status != 'Complete'
        """)
        active_progress_batches = cur.fetchall()
        
        batch_progress = []
        is_qc_stage = lambda name: name.lower() in ("qc", "quality check", "quality", "final qc", "quality control")
        
        for batch in active_progress_batches:
            batch_id = batch["batch_id"]
            product_id = batch["product_id"]
            target_qty = batch["target_qty"]
            
            cur.execute("""
                SELECT component_id, quantity_required
                FROM junction_of_materials
                WHERE product_id = %s
            """, (product_id,))
            bom = cur.fetchall()
            
            cur.execute("""
                SELECT stage_name 
                FROM batch_stages 
                WHERE batch_id = %s
            """, (batch_id,))
            all_stages = cur.fetchall()
            stages = [s["stage_name"] for s in all_stages if not is_qc_stage(s["stage_name"])]
            
            total_required = 0
            total_consumed = 0
            
            for item in bom:
                comp_id = item["component_id"]
                req_qty = item["quantity_required"] * target_qty
                
                for stage in stages:
                    total_required += req_qty
                    cur.execute("""
                        SELECT COALESCE(SUM(qty_used), 0) AS total
                        FROM component_consumption
                        WHERE batch_id = %s AND component_id = %s AND stage_name = %s
                    """, (batch_id, comp_id, stage))
                    consumed = cur.fetchone()["total"] or 0
                    total_consumed += min(consumed, req_qty)
                    
            percent_complete = (
                round(total_consumed / total_required * 100, 2)
                if total_required > 0 else 0.0
            )
            
            batch_progress.append({
                "batch_id": batch_id,
                "product_name": batch["product_name"],
                "target_qty": target_qty,
                "completed_qty": batch["completed_qty"],
                "status": batch["status"],
                "percent_complete": percent_complete
            })

        # Workload summary: Active Component Workload Summary
        # Get all active batches
        cur.execute("""
            SELECT pb.batch_id, pb.product_id, pb.target_qty 
            FROM production_batches pb
            WHERE pb.status != 'Complete'
        """)
        active_batches = cur.fetchall()

        workload_summary = []
        is_qc_stage = lambda name: name.lower() in ("qc", "quality check", "quality", "final qc", "quality control")

        for batch in active_batches:
            batch_id = batch["batch_id"]
            product_id = batch["product_id"]
            target_qty = batch["target_qty"]

            # Get BOM components for this product
            cur.execute("""
                SELECT jom.component_id, jom.quantity_required, c.part_name
                FROM junction_of_materials jom
                JOIN components c ON jom.component_id = c.component_id
                WHERE jom.product_id = %s
            """, (product_id,))
            bom_items = cur.fetchall()

            # Get production stages for this batch
            cur.execute("""
                SELECT stage_name, status, stage_id 
                FROM batch_stages 
                WHERE batch_id = %s 
                ORDER BY stage_id ASC
            """, (batch_id,))
            all_stages = cur.fetchall()
            production_stages = [s["stage_name"] for s in all_stages if not is_qc_stage(s["stage_name"])]

            if not production_stages:
                continue

            for bom in bom_items:
                comp_id = bom["component_id"]
                part_name = bom["part_name"]
                req_qty_per_unit = bom["quantity_required"]
                target_qty_for_comp = req_qty_per_unit * target_qty

                # Find the current stage of this component
                # It is the first stage in production_stages where total consumed in that stage < target_qty_for_comp
                current_comp_stage = None
                qty_consumed_in_current_stage = 0

                for stage in production_stages:
                    cur.execute("""
                        SELECT COALESCE(SUM(qty_used), 0) AS total
                        FROM component_consumption
                        WHERE batch_id = %s AND component_id = %s AND stage_name = %s
                    """, (batch_id, comp_id, stage))
                    total_consumed = cur.fetchone()["total"] or 0

                    if total_consumed < target_qty_for_comp:
                        current_comp_stage = stage
                        qty_consumed_in_current_stage = total_consumed
                        break

                # If current_comp_stage is None, it means the component has completed all production stages!
                # In that case, it is removed from workload_summary!
                if current_comp_stage is not None:
                    workload_summary.append({
                        "component_id": comp_id,
                        "part_name": part_name,
                        "quantity_consumed": int(qty_consumed_in_current_stage),
                        "stage_name": f"{current_comp_stage} ({batch_id})"
                    })

        # Calculate forecasting from completed batches in the previous 7 days
        cur.execute("""
            SELECT p.product_name AS part_name, dp.predicted_demand_qty
            FROM demand_predictions dp
            JOIN products p ON dp.product_id = p.product_id
        """)
        predicted_rows = cur.fetchall()

        demand_forecasts = []
        for r in predicted_rows:
            demand_forecasts.append({
                "part_name": r["part_name"],
                "predicted_demand_qty": int(r["predicted_demand_qty"])
            })

        # Get finished products ready for QC alerts
        from completion_helper import is_batch_production_complete
        cur.execute("""
            SELECT pb.batch_id, pb.product_id 
            FROM production_batches pb
            JOIN finished_goods fg ON pb.batch_id = fg.batch_id
            WHERE fg.qc_status = 'Pending QC'
        """)
        candidates = cur.fetchall()
        
        finished_product_alerts = []
        for b in candidates:
            if is_batch_production_complete(cur, b["batch_id"]):
                # Retrieve product name
                cur.execute("SELECT product_name FROM products WHERE product_id = %s", (b["product_id"],))
                p_row = cur.fetchone()
                p_name = p_row["product_name"] if p_row else "Product"
                
                finished_product_alerts.append({
                    "batch_id": b["batch_id"],
                    "part_name": f"Finished Product ({p_name})",
                    "is_fg_alert": True
                })

        alerts_list = []
        for comp in low_stock_alerts:
            alerts_list.append({
                "component_id": comp["component_id"],
                "part_name": comp["part_name"],
                "warehouse_stock": comp["warehouse_stock"],
                "floor_stock": comp["floor_stock"],
                "min_threshold": comp["min_threshold"],
                "is_fg_alert": False
            })
            
        for fpa in finished_product_alerts:
            alerts_list.append({
                "batch_id": fpa["batch_id"],
                "part_name": fpa["part_name"],
                "is_fg_alert": True
            })

    return jsonify({
        "active_alerts": {
            "count": len(alerts_list),
            "items": alerts_list,
        },
        "pending_requests": pending_requests,
        "qc_pass_percentage": qc_pass_percentage,
        "qc_fail_percentage": qc_fail_percentage,
        "batch_progress": batch_progress,
        "workload_summary": workload_summary,
        "demand_forecasts": demand_forecasts,
    }), 200


@supervisor_bp.route("/api/dashboard/supervisor/place-order", methods=["POST"])
@login_required
@role_required("Supervisor")
def place_order_from_alert():
    data = request.get_json(silent=True) or {}
    component_id = data.get("component_id")

    if not component_id:
        return jsonify({"error": "component_id is required"}), 400

    with get_db_cursor(commit=True) as cur:
        cur.execute("""
            SELECT component_id, warehouse_stock, floor_stock, min_threshold 
            FROM components WHERE component_id = %s FOR UPDATE
        """, (component_id,))
        comp = cur.fetchone()
        if not comp:
            return jsonify({"error": f"Unknown component_id '{component_id}'"}), 404

        # Calculate shortage
        current_stock = comp["warehouse_stock"] + comp["floor_stock"]
        shortage = comp["min_threshold"] - current_stock
        recommended_qty = max(shortage, 0)
        
        # Fallback to threshold if recommended is 0
        if recommended_qty == 0:
            recommended_qty = comp["min_threshold"]

        cur.execute("""
            INSERT INTO material_requests (component_id, requested_qty, status)
            VALUES (%s, %s, 'Pending')
        """, (component_id, recommended_qty))
        request_id = cur.lastrowid

    return jsonify({
        "message": "Material request generated",
        "request_id": request_id,
        "component_id": component_id,
        "requested_qty": recommended_qty,
        "status": "Pending",
        "requested_by": g.user_id,
    }), 201
