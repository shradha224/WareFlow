# Wareflow Backend — API List

Base URL (local dev): `http://localhost:5000`

All endpoints except `/api/login` and `/api/health` require:
```
Authorization: Bearer <token>
```
(token returned by `POST /api/login`)

---

## 1. Auth

### `POST /api/login`
Login page. Validates credentials, identifies role, creates session.
- **Auth:** none
- **Body:** `{ "user_id": "string", "password": "string" }`
- **Response 200:** `{ "token", "user_id", "user_role", "redirect_to" }`
- **Response 401:** `{ "error": "Invalid username or password" }`

---

## 2. Supervisor Dashboard

### `GET /api/dashboard/supervisor`
Fetches alerts, pending requests, QC %, batch progress, workload, demand forecasts.
- **Auth:** Supervisor
- **Response 200:** `{ active_alerts, pending_requests, qc_pass_percentage, batch_progress, workload_summary, demand_forecasts }`

### `POST /api/dashboard/supervisor/place-order`
Generates a material request from a low-stock alert card.
- **Auth:** Supervisor
- **Body:** `{ "component_id": "string", "requested_qty": number }`
- **Response 201:** `{ message, request_id, component_id, requested_qty, status, requested_by }`

---

## 3. Warehouse Inventory

### `GET /api/inventory`
Retrieves all components with computed stock status.
- **Auth:** any logged-in user
- **Response 200:** `{ "inventory": [ { component_id, part_name, description, warehouse_stock, floor_stock, min_threshold, total_stock, stock_status } ] }`

---

## 4. Launch Batch

### `POST /api/batches`
Generates a Batch ID and initializes a production batch.
- **Auth:** Supervisor, Worker
- **Body:** `{ "product_name": "string", "target_qty": number }`
- **Response 201:** `{ message, batch_id, product_name, target_qty, completed_qty, status }`

### `POST /api/batches/<batch_id>/stages`
Creates or updates stage targets for a batch.
- **Auth:** Supervisor, Worker
- **Body:** `{ "stages": [ { "stage_name": "string", "target_hours": number }, ... ] }`
- **Response 200:** `{ batch_id, stages: [ { stage_id, stage_name, action } ] }`

---

## 5. System Reports

### `GET /api/reports?log_limit=50`
Calculates averages (delay, completion time, QC pass rate) and returns recent activity logs.
- **Auth:** any logged-in user
- **Query:** `log_limit` (optional, default 50)
- **Response 200:** `{ averages: { avg_delay_hours, avg_completion_hours, avg_qc_pass_rate_percent }, logs: [...] }`

---

## 6. Request Raw Material

### `POST /api/material-requests`
Submits a new raw material request (status = Pending).
- **Auth:** any logged-in user
- **Body:** `{ "component_id": "string", "requested_qty": number }`
- **Response 201:** `{ message, request_id, component_id, requested_qty, status, submitted_by }`

---

## 7. Warehouse Stock Control

### `POST /api/stock/dispatch`
Dispatches material from warehouse stock, creates a material_transfers record.
- **Auth:** Supervisor, Inventory Inspector
- **Body:** `{ "component_id": "string", "dispatched_qty": number }`
- **Response 201:** `{ message, transfer_id, component_id, dispatched_qty, transfer_status }`
- **Response 409:** insufficient stock

### `POST /api/inventory/items`
Adds a new inventory item, generates a Component ID.
- **Auth:** Supervisor, Inventory Inspector
- **Body:** `{ "part_name": "string", "description": "string", "min_threshold": number, "warehouse_stock": number, "floor_stock": number }`
- **Response 201:** `{ message, component_id, part_name, description, warehouse_stock, floor_stock, min_threshold }`

---

## 8. QC Check (incoming components)

### `POST /api/qc/component`
Records a Pass/Fail QC result for an incoming component batch.
- **Auth:** Inventory Inspector, Supervisor
- **Body:** `{ "component_id": "string", "qty_inspected": number, "result": "Pass" | "Fail" }`
- **Response 201:** `{ message, inspection_id, component_id, result, qty_inspected, quality_metrics }`

---

## 9. Raw Material Requests

### `PATCH /api/material-requests/<request_id>`
Approves, fulfils, or rejects a material request.
- **Auth:** Supervisor, Inventory Inspector
- **Body:** `{ "action": "approve" | "fulfil" | "reject" }`
- **Response 200:** `{ message, request_id, status, [transfer_id, moved_to] }`

---

## 10. Floor Material Intake

### `PATCH /api/transfers/<transfer_id>/verify`
Marks a material transfer as received, adds quantity to floor stock.
- **Auth:** Worker, Inventory Inspector
- **Response 200:** `{ message, transfer_id, component_id, qty_added_to_floor_stock }`
- **Response 409:** already received

---

## 11. Component Consumption

### `POST /api/consumption`
Logs component consumption on a batch/stage, advances the batch and (if target reached) closes out the stage and moves to the next one.
- **Auth:** Worker, Supervisor
- **Body:** `{ "batch_id": "string", "component_id": "string", "stage_name": "string", "qty_used": number, "units_completed": number (optional, default 1) }`
- **Response 201:** `{ message, consumption_id, batch_id, completed_qty, target_qty, target_reached, stage_closure }`
- **Response 409:** insufficient floor stock

---

## 12. Quality Check (finished goods)

### `POST /api/qc/finished-good`
Records a Pass/Fail QC result at batch/finished-good level.
- **Auth:** Inventory Inspector, Supervisor
- **Body:** `{ "batch_id": "string", "finished_good_id": "string" (optional), "qty_inspected": number, "result": "Pass" | "Fail" }`
- **Response 201:** `{ message, inspection_id, batch_id, result, finished_good, quality_counts }`

---

## 13. Background Jobs / Ops

### `POST /api/jobs/run/<job_name>`
Manually triggers a background process (normally run on a schedule — see `scheduler.py`).
- **Auth:** Supervisor
- **Path param `job_name`:** one of `low_stock_detection`, `delay_detection`, `batch_completion`, `finished_good_generation`, `demand_prediction`
- **Response 200:** `{ job, triggered_by, result }`
- **Response 404:** unknown job name

### `GET /api/health`
Basic liveness check.
- **Auth:** none
- **Response 200:** `{ "status": "ok" }`

---

## Quick index

| Method | Path |
|---|---|
| POST | `/api/login` |
| GET | `/api/dashboard/supervisor` |
| POST | `/api/dashboard/supervisor/place-order` |
| GET | `/api/inventory` |
| POST | `/api/batches` |
| POST | `/api/batches/<batch_id>/stages` |
| GET | `/api/reports` |
| POST | `/api/material-requests` |
| POST | `/api/stock/dispatch` |
| POST | `/api/inventory/items` |
| POST | `/api/qc/component` |
| PATCH | `/api/material-requests/<request_id>` |
| PATCH | `/api/transfers/<transfer_id>/verify` |
| POST | `/api/consumption` |
| POST | `/api/qc/finished-good` |
| POST | `/api/jobs/run/<job_name>` |
| GET | `/api/health` |
