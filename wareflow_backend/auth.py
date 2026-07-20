"""
auth.py
-------
Used on the LOGIN PAGE.
Table row implemented:
  Page  | User Action                    | System Action
  Login | Enter username and password    | Validate credentials, identify
        |                                | role, create user session,
        |                                | redirect to role-based dashboard

Backed by the `Users` table (user_id, password, user_role).
"""

import jwt
import bcrypt
import datetime
from functools import wraps
from flask import request, jsonify, g
from config import Config
from db import get_db_cursor


# ---------- password helpers ----------

def hash_password(plain_password: str) -> str:
    return bcrypt.hashpw(plain_password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain_password.encode("utf-8"), hashed.encode("utf-8"))


# ---------- session (JWT) helpers ----------

def create_session_token(user_id: str, user_role: str) -> str:
    payload = {
        "user_id": user_id,
        "user_role": user_role,
        "exp": datetime.datetime.utcnow() + datetime.timedelta(minutes=Config.JWT_EXPIRY_MINUTES),
        "iat": datetime.datetime.utcnow(),
    }
    return jwt.encode(payload, Config.JWT_SECRET, algorithm="HS256")


def decode_session_token(token: str):
    return jwt.decode(token, Config.JWT_SECRET, algorithms=["HS256"])


# ---------- core login logic (called by routes/login.py) ----------

# Maps each role to the dashboard the frontend should redirect to.
ROLE_DASHBOARD_MAP = {
    "Supervisor": "/dashboard/supervisor",
    "Inventory Inspector": "/dashboard/inventory",
    "Worker": "/dashboard/worker",
}


def authenticate_user(user_id: str, password: str):
    """
    Validates credentials against the Users table, identifies role.
    Returns (success, payload_or_error).
    """
    with get_db_cursor() as cur:
        cur.execute(
            "SELECT user_id, password, user_role FROM users WHERE user_id = %s",
            (user_id,),
        )
        user = cur.fetchone()
        print("User fetched:", user)

    if not user or not verify_password(password, user["password"]):
        return False, {"error": "Invalid username or password"}

    token = create_session_token(user["user_id"], user["user_role"])
    redirect_to = ROLE_DASHBOARD_MAP.get(user["user_role"], "/dashboard")

    return True, {
        "token": token,
        "user_id": user["user_id"],
        "user_role": user["user_role"],
        "redirect_to": redirect_to,
    }


# ---------- decorators used by every other route file ----------

def login_required(fn):
    """Validates the JWT session and attaches g.user_id / g.user_role."""
    @wraps(fn)
    def wrapper(*args, **kwargs):
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return jsonify({"error": "Missing or malformed Authorization header"}), 401
        token = auth_header.split(" ", 1)[1]
        try:
            payload = decode_session_token(token)
        except jwt.ExpiredSignatureError:
            return jsonify({"error": "Session expired, please log in again"}), 401
        except jwt.InvalidTokenError:
            return jsonify({"error": "Invalid session token"}), 401

        g.user_id = payload["user_id"]
        g.user_role = payload["user_role"]
        return fn(*args, **kwargs)
    return wrapper


def role_required(*allowed_roles):
    """Stack under @login_required to restrict a route to specific roles."""
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            if g.get("user_role") not in allowed_roles:
                return jsonify({"error": "You do not have permission to perform this action"}), 403
            return fn(*args, **kwargs)
        return wrapper
    return decorator
