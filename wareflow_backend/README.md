# Wareflow Backend

Flask + PyMySQL backend implementing the endpoints from *System Architecture
Support Tables* against the `wareflow_db` schema in `wareflow_sql1.sql`.

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env      # fill in your DB credentials + JWT secret
mysql -u root -p < wareflow_sql1.sql   # create the schema
python app.py              # runs on http://localhost:5000
```

Passwords in `Users.password` must be stored with `auth.hash_password()`
(bcrypt) — insert your first user with a short Python one-liner:
```python
from auth import hash_password
print(hash_password("your-password"))
```

## File map (where each piece of backend code is used)

| File | Used on / for |
|---|---|
| `config.py` | App-wide settings (DB, JWT, stage order, job intervals) |
| `db.py` | DB connection helper used by every route and job |
| `auth.py` | Login page logic + `@login_required` / `@role_required` guards used on every other page |
| `routes/login.py` | **Login page** |
| `routes/supervisor_dashboard.py` | **Supervisor Dashboard page** (view + "Place Order" action) |
| `routes/warehouse_inventory.py` | **Warehouse Inventory page** |
| `routes/launch_batch.py` | **Launch Batch page** (initialize batch, set stage targets) |
| `routes/system_reports.py` | **System Reports page** |
| `routes/request_raw_material.py` | **Request Raw Material page** |
| `routes/warehouse_stock_control.py` | **Warehouse Stock Control page** (dispatch, add item) |
| `routes/qc_check.py` | **QC Check page** (incoming component inspection) |
| `routes/raw_material_requests.py` | **Raw Material Requests page** (approve/fulfil) |
| `routes/floor_material_intake.py` | **Floor Material Intake page** (verify received) |
| `routes/component_consumption.py` | **Component Consumption page** (mark complete, stage advancement) |
| `routes/quality_check.py` | **Quality Check page** (finished-good QC) |
| `background_jobs.py` | The 5 **Background System Processes** |
| `scheduler.py` | Runs `background_jobs.py` automatically on intervals (started in `app.py`) |
| `app.py` | Registers everything, exposes a manual job trigger for ops/testing |

## Endpoint reference

| Method & Path | Page | Maps to system action |
|---|---|---|
| `POST /api/login` | Login | Validate credentials, identify role, create session, redirect |
| `GET /api/dashboard/supervisor` | Supervisor Dashboard | Fetch alerts, pending requests, QC %, batch progress, workload, demand data |
| `POST /api/dashboard/supervisor/place-order` | Supervisor Dashboard | Generate material request from a low-stock alert |
| `GET /api/inventory` | Warehouse Inventory | Retrieve inventory + stock status |
| `POST /api/batches` | Launch Batch | Generate Batch ID, initialize batch |
| `POST /api/batches/<batch_id>/stages` | Launch Batch | Create/update stage targets |
| `GET /api/reports` | System Reports | Averages + activity logs |
| `POST /api/material-requests` | Request Raw Material | Generate Request ID, status = Pending |
| `POST /api/stock/dispatch` | Warehouse Stock Control | Reduce warehouse stock, create transfer |
| `POST /api/inventory/items` | Warehouse Stock Control | Generate Component ID, create item |
| `POST /api/qc/component` | QC Check | Store QC result, update metrics |
| `PATCH /api/material-requests/<id>` | Raw Material Requests | Approve/fulfil, move to Raw Material QC |
| `PATCH /api/transfers/<id>/verify` | Floor Material Intake | Update transfer status + timestamp |
| `POST /api/consumption` | Component Consumption | Reduce floor stock, log, advance stage |
| `POST /api/qc/finished-good` | Quality Check | Update quality counts, Finished_Goods.qc_status |
| `POST /api/jobs/run/<job_name>` | (ops) | Manually trigger any background process |

## Background processes (`background_jobs.py`)

| Job | System action |
|---|---|
| `low_stock_detection` | Checks inventory vs threshold, auto-raises a Pending material request per shortfall |
| `delay_detection` | Compares actual vs target stage duration, flags `is_delayed` |
| `batch_completion` | `completed_qty >= target_qty` -> `status = 'Complete'` |
| `finished_good_generation` | Generates a Finished Good ID for completed batches, sets `qc_status = 'Pending QC'` |
| `demand_prediction` | Moving-average forecast per component, written to `Demand_Forecasts` |

## Notes on schema mapping

- The spec mentions a `FloorHouseInventory` record; the schema doesn't have
  that table, so **`Material_Transfers`** plays that role (dispatch ->
  `In Transit`, then Floor Material Intake marks it `Received` and adds the
  quantity onto `Components.floor_stock`).
- "Move to Raw Material QC" (Raw Material Requests page) is implemented as
  creating an `In Transit` `Material_Transfers` row, which Floor Material
  Intake later verifies — this is the same pipeline QC/floor staff use for
  regular dispatches.
- Stage progression uses a configurable `STAGE_ORDER` (see `config.py` /
  `.env.example`) since the schema doesn't encode stage sequence explicitly.
