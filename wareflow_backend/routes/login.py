"""
routes/login.py
----------------
USED ON: Login page.

Endpoint:
  POST /api/login   { user_id, password } -> validates credentials,
                     identifies role, creates session, tells frontend
                     which role-based dashboard to redirect to.
"""

from flask import Blueprint, request, jsonify
from auth import authenticate_user

login_bp = Blueprint("login", __name__)


@login_bp.route("/api/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or {}
    user_id = data.get("user_id")
    password = data.get("password")

    if not user_id or not password:
        return jsonify({"error": "user_id and password are required"}), 400

    success, payload = authenticate_user(user_id, password)
    if not success:
        return jsonify(payload), 401

    return jsonify(payload), 200
