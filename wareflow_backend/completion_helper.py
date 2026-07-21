def is_batch_production_complete(cur, batch_id) -> bool:
    # 1. Get batch details
    cur.execute("SELECT product_id, target_qty FROM production_batches WHERE batch_id = %s", (batch_id,))
    batch = cur.fetchone()
    if not batch:
        return False
    
    product_id = batch["product_id"]
    target_qty = batch["target_qty"]

    # 2. Get all required components from BOM
    cur.execute("""
        SELECT component_id, quantity_required 
        FROM junction_of_materials 
        WHERE product_id = %s
    """, (product_id,))
    bom_items = cur.fetchall()
    if not bom_items:
        return False

    # 3. Get all production stages for this batch (excluding QC stages)
    cur.execute("""
        SELECT stage_name 
        FROM batch_stages 
        WHERE batch_id = %s 
        ORDER BY stage_id ASC
    """, (batch_id,))
    all_stages = cur.fetchall()
    
    is_qc_stage = lambda name: name.lower() in ("qc", "quality check", "quality", "final qc", "quality control")
    production_stages = [s["stage_name"] for s in all_stages if not is_qc_stage(s["stage_name"])]
    if not production_stages:
        return False

    # 4. Verify that EVERY required component has completed EVERY production stage
    for bom in bom_items:
        comp_id = bom["component_id"]
        req_qty = bom["quantity_required"] * target_qty
        
        for stage in production_stages:
            cur.execute("""
                SELECT SUM(qty_used) AS total_consumed
                FROM component_consumption
                WHERE batch_id = %s AND component_id = %s AND stage_name = %s
            """, (batch_id, comp_id, stage))
            consumed = cur.fetchone()["total_consumed"] or 0
            if consumed < req_qty:
                return False

    return True
