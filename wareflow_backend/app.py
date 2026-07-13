"""
app.py
------
Entry point for the Wareflow backend.

Wires together:
  - One blueprint per page (routes/*.py), matching the
    "Page -> User Action -> System Action" table.
  - The 5 background system processes (background_jobs.py), run on a
    schedule by scheduler.py, and also triggerable on demand below for
    ops/testing.

Run with:  python app.py   (dev)
           gunicorn -w 4 -b 0.0.0.0:5000 'app:create_app()'   (prod)
"""

from flask import Flask, jsonify, g
from auth import login_required, role_required
import background_jobs as jobs
from scheduler import start_scheduler

from routes.login import login_bp
from routes.supervisor_dashboard import supervisor_bp
from routes.warehouse_inventory import warehouse_inventory_bp
from routes.launch_batch import launch_batch_bp
from routes.system_reports import system_reports_bp
from routes.request_raw_material import request_raw_material_bp
from routes.warehouse_stock_control import warehouse_stock_control_bp
from routes.qc_check import qc_check_bp
from routes.raw_material_requests import raw_material_requests_bp
from routes.floor_material_intake import floor_material_intake_bp
from routes.component_consumption import component_consumption_bp
from routes.quality_check import quality_check_bp


def create_app():
    app = Flask(__name__)

    for bp in (
        login_bp,
        supervisor_bp,
        warehouse_inventory_bp,
        launch_batch_bp,
        system_reports_bp,
        request_raw_material_bp,
        warehouse_stock_control_bp,
        qc_check_bp,
        raw_material_requests_bp,
        floor_material_intake_bp,
        component_consumption_bp,
        quality_check_bp,
    ):
        app.register_blueprint(bp)

    @app.route("/api/health", methods=["GET"])
    def health():
        return jsonify({"status": "ok"}), 200

    @app.route("/api/jobs/run/<job_name>", methods=["POST"])
    @login_required
    @role_required("Supervisor")
    def run_job_manually(job_name):
        """Manual trigger for any background process, e.g. for ops/testing."""
        job_fn = jobs.JOB_REGISTRY.get(job_name)
        if not job_fn:
            return jsonify({"error": f"Unknown job '{job_name}'", "available_jobs": list(jobs.JOB_REGISTRY.keys())}), 404
        result = job_fn()
        return jsonify({"job": job_name, "triggered_by": g.user_id, "result": result}), 200

    @app.errorhandler(404)
    def not_found(_):
        return jsonify({"error": "Not found"}), 404

    @app.errorhandler(500)
    def server_error(_):
        return jsonify({"error": "Internal server error"}), 500

    start_scheduler()
    return app


if __name__ == "__main__":
    application = create_app()
    application.run(host="0.0.0.0", port=5000, debug=True)
