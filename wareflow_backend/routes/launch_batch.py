"""
routes/launch_batch.py
-----------------------
USED ON: Launch Batch page.

Endpoints:
  POST /api/batches
       { product_name, target_qty }
       -> Generate Batch ID, create batch record, initialize
          completed_qty = 0 and status = 'Initialized'.

  POST /api/batches/<batch_id>/stages
       { stages: [ { stage_name, target_hours }, ... ] }
       -> Create/update Batch_Stages records and store target values.
"""

import uuid
from flask import Blueprint, request, jsonify
from auth import login_required, role_required
from db import get_db_cursor

launch_batch_bp = Blueprint("launch_batch", __name__)


def _generate_batch_id() -> str:
    return f"BATCH-{uuid.uuid4().hex[:8].upper()}"
STAGE_MAP = {
    "assembly": "Assembly",
    "quality": "QC",
    "packaging": "Packaging",
    "dispatch": "Dispatch"
}

@launch_batch_bp.route("/api/products", methods=["GET"])
@login_required
def get_products():
    with get_db_cursor() as cur:
        cur.execute("""
            SELECT product_name
            FROM Products
            ORDER BY product_name
        """)
        products = cur.fetchall()

    return jsonify(products), 200

@launch_batch_bp.route("/api/batches/active", methods=["GET"])
@login_required
def get_active_batches():
    with get_db_cursor() as cur:
        cur.execute("""
            SELECT pb.batch_id, p.product_name, pb.target_qty, pb.completed_qty, pb.status, pb.created_at
            FROM Production_Batches pb
            JOIN Products p ON pb.product_id = p.product_id
            WHERE pb.status != 'Complete'
            ORDER BY pb.created_at DESC
        """)
        batches = cur.fetchall()
    return jsonify({"batches": batches}), 200

@launch_batch_bp.route("/api/batches", methods=["POST"])
@login_required
@role_required("Supervisor", "Worker")
def initialize_batch():
    data = request.get_json(silent=True) or {}
    product_name = data.get("product_name")
    target_qty = data.get("target_qty")

    if not product_name or not target_qty:
        return jsonify({"error": "product_name and target_qty are required"}), 400

    batch_id = _generate_batch_id()

    with get_db_cursor(commit=True) as cur:
        cur.execute("SELECT product_id FROM Products WHERE product_name = %s", (product_name,))
        product_row = cur.fetchone()
        if not product_row:
            return jsonify({"error": f"Unknown product '{product_name}'"}), 404
        product_id = product_row["product_id"]

        cur.execute("""
            INSERT INTO Production_Batches (batch_id, product_id, target_qty, completed_qty, status)
            VALUES (%s, %s, %s, 0, 'Initialized')
        """, (batch_id, product_id, target_qty))

        # Determine the required components automatically from junction_of_materials
        cur.execute("""
            SELECT component_id, quantity_required
            FROM junction_of_materials
            WHERE product_id = %s
        """, (product_id,))
        bom_items = cur.fetchall()

        for item in bom_items:
            req_qty = item["quantity_required"] * target_qty
            # Get warehouse stock for this component
            cur.execute("""
                SELECT warehouse_stock, floor_stock, min_threshold
                FROM Components
                WHERE component_id = %s
                FOR UPDATE
            """, (item["component_id"],))
            comp = cur.fetchone()
            
            if not comp or comp["warehouse_stock"] < req_qty:
                # Case B: Insufficient warehouse stock -> Generate pending material request
                cur.execute("""
                    INSERT INTO Material_Requests (component_id, requested_qty, status, batch_id)
                    VALUES (%s, %s, 'Pending', %s)
                """, (item["component_id"], req_qty, batch_id))

        # Stage Initialization: Retrieve Product Workflow or fallback to defaults
        cur.execute("""
            SELECT stage_name 
            FROM Product_Workflow 
            WHERE product_id = %s 
            ORDER BY sequence_order ASC
        """, (product_id,))
        workflow_rows = cur.fetchall()

        if workflow_rows:
            stages_to_init = []
            for i, row in enumerate(workflow_rows):
                stg_name = row["stage_name"]
                status = "In Progress" if i == 0 else "Pending"
                start_ts = "CURRENT_TIMESTAMP" if i == 0 else "NULL"
                stages_to_init.append((stg_name, 0.0, status, start_ts))
        else:
            # Fallback to default stages if no product workflow is configured
            stages_to_init = [
                ("Assembly", 0.0, "In Progress", "CURRENT_TIMESTAMP"),
                ("QC", 0.0, "Pending", "NULL"),
                ("Packaging", 0.0, "Pending", "NULL"),
                ("Dispatch", 0.0, "Pending", "NULL")
            ]

        for stage_name, target_hours, status, start_ts in stages_to_init:
            sql = f"""
                INSERT INTO Batch_Stages (batch_id, stage_name, target_hours, target_qty, status, start_timestamp)
                VALUES (%s, %s, %s, 0, %s, {start_ts})
            """
            cur.execute(sql, (batch_id, stage_name, target_hours, status))


    return jsonify({
        "message": "Batch initialized",
        "batch_id": batch_id,
        "product_name": product_name,
        "target_qty": target_qty,
        "completed_qty": 0,
        "status": "Initialized",
    }), 201


@launch_batch_bp.route("/api/batches/<batch_id>/stages", methods=["POST"])
@login_required
@role_required("Supervisor", "Worker")
def set_batch_stages(batch_id):
    data = request.get_json(silent=True) or {}
    stages = data.get("stages")

    if not stages or not isinstance(stages, list):
        return jsonify({"error": "stages must be a non-empty list of {stage_name, target_hours}"}), 400

    with get_db_cursor(commit=True) as cur:
        cur.execute("SELECT batch_id FROM Production_Batches WHERE batch_id = %s", (batch_id,))
        if not cur.fetchone():
            return jsonify({"error": f"Unknown batch_id '{batch_id}'"}), 404

        created_or_updated = []
        for stage in stages:
            stage_name = stage.get("stage_name")
            target_hours = stage.get("target_hours")
            target_qty = stage.get("target_qty", 0)
            if not stage_name or target_hours is None:
                continue

            stage_name_db = STAGE_MAP.get(stage_name.lower(), stage_name)

            cur.execute("""
                SELECT stage_id FROM Batch_Stages
                WHERE batch_id = %s AND stage_name = %s
            """, (batch_id, stage_name_db))
            existing = cur.fetchone()

            if existing:
                cur.execute("""
                    UPDATE Batch_Stages SET target_hours = %s, target_qty = %s
                    WHERE stage_id = %s
                """, (target_hours, target_qty, existing["stage_id"]))
                created_or_updated.append({"stage_id": existing["stage_id"], "stage_name": stage_name_db, "action": "updated"})
            else:
                cur.execute("""
                    INSERT INTO Batch_Stages (batch_id, stage_name, target_hours, target_qty, status)
                    VALUES (%s, %s, %s, %s, 'In Progress')
                """, (batch_id, stage_name_db, target_hours, target_qty))
                created_or_updated.append({"stage_id": cur.lastrowid, "stage_name": stage_name_db, "action": "created"})

    return jsonify({"batch_id": batch_id, "stages": created_or_updated}), 200


@launch_batch_bp.route("/api/batches/<batch_id>/stages", methods=["GET"])
@login_required
def get_batch_stages(batch_id):
    with get_db_cursor() as cur:
        cur.execute("SELECT batch_id FROM Production_Batches WHERE batch_id = %s", (batch_id,))
        if not cur.fetchone():
            return jsonify({"error": f"Unknown batch_id '{batch_id}'"}), 404

        cur.execute("""
            SELECT stage_id, stage_name, target_hours, target_qty, status
            FROM Batch_Stages
            WHERE batch_id = %s
            ORDER BY stage_id ASC
        """, (batch_id,))
        stages = cur.fetchall()
        for s in stages:
            s["target_hours"] = float(s["target_hours"])
            s["target_qty"] = int(s["target_qty"]) if s.get("target_qty") is not None else 0
    return jsonify({"stages": stages}), 200


@launch_batch_bp.route("/api/products", methods=["POST"])
@login_required
@role_required("Supervisor", "Inventory Inspector")
def add_new_product():
    data = request.get_json(silent=True) or {}
    product_name = data.get("product_name")
    description = data.get("description", "")
    components = data.get("components")
    stages = data.get("stages")  # Ordered list of stage names (strings)

    if not product_name:
        return jsonify({"error": "product_name is required"}), 400
    if not components or not isinstance(components, list):
        return jsonify({"error": "components mapping list is required"}), 400

    product_id = f"PROD-{uuid.uuid4().hex[:8].upper()}"

    with get_db_cursor(commit=True) as cur:
        cur.execute("SELECT product_id FROM Products WHERE product_name = %s", (product_name,))
        if cur.fetchone():
            return jsonify({"error": f"Product with name '{product_name}' already exists"}), 409

        cur.execute("""
            INSERT INTO Products (product_id, product_name, description)
            VALUES (%s, %s, %s)
        """, (product_id, product_name, description))

        for comp in components:
            comp_id = comp.get("component_id")
            qty_req = comp.get("quantity_required")
            if not comp_id or not qty_req:
                continue
            cur.execute("""
                INSERT INTO junction_of_materials (product_id, component_id, quantity_required)
                VALUES (%s, %s, %s)
            """, (product_id, comp_id, qty_req))

        if stages and isinstance(stages, list):
            seq_order = 1
            for stage in stages:
                if isinstance(stage, str) and stage.strip():
                    cur.execute("""
                        INSERT INTO Product_Workflow (product_id, stage_name, sequence_order)
                        VALUES (%s, %s, %s)
                    """, (product_id, stage.strip(), seq_order))
                    seq_order += 1

    # Trigger initial demand prediction generation
    from background_jobs import demand_prediction
    try:
        demand_prediction()
    except Exception as e:
        print(f"Error generating initial demand prediction: {e}")

    return jsonify({
        "message": "Product, component mapping, and workflow created",
        "product_id": product_id,
        "product_name": product_name,
        "description": description,
        "components": components,
        "stages": stages
    }), 201

