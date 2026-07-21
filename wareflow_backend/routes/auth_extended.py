import datetime
import json
import re
import random
from flask import Blueprint, request, jsonify
from auth import hash_password
from db import get_db_cursor
from email_service import send_otp_email

auth_extended_bp = Blueprint("auth_extended", __name__)

def is_valid_email(email):
    return re.match(r"^[^\s@]+@[^\s@]+\.[^\s@]+$", email) is not None

def check_password_complexity(password):
    if len(password) < 8:
        return False
    if not any(c.isupper() for c in password):
        return False
    if not any(c.islower() for c in password):
        return False
    if not any(c.isdigit() for c in password):
        return False
    # Check for special characters (either standard punctuation or non-alphanumeric)
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password) and not re.search(r"[^A-Za-z0-9]", password):
        return False
    return True

@auth_extended_bp.route("/api/check-userid", methods=["POST"])
def check_userid():
    data = request.get_json(silent=True) or {}
    user_id = data.get("user_id", "").strip()
    
    if not user_id:
        return jsonify({"available": False, "error": "User ID is required"}), 400
        
    with get_db_cursor() as cur:
        # Check active users
        cur.execute("SELECT user_id FROM users WHERE user_id = %s", (user_id,))
        if cur.fetchone():
            return jsonify({"available": False, "error": "User ID already exists"}), 200
            
        # Check pending registration payloads
        cur.execute("""
            SELECT payload FROM email_verification 
            WHERE purpose = 'Registration' AND expiry_time > NOW()
        """)
        rows = cur.fetchall()
        for row in rows:
            payload_str = row.get("payload")
            if payload_str:
                try:
                    payload = json.loads(payload_str)
                    if payload.get("user_id") == user_id:
                        return jsonify({"available": False, "error": "User ID already exists"}), 200
                except Exception:
                    pass
                    
    return jsonify({"available": True}), 200

@auth_extended_bp.route("/api/register", methods=["POST"])
def register():
    print("Registration request received", flush=True)
    data = request.get_json(silent=True) or {}
    user_id = data.get("user_id", "").strip()
    full_name = data.get("full_name", "").strip()
    username = data.get("username", "").strip() or None
    email = data.get("email", "").strip()
    phone_number = data.get("phone_number", "").strip()
    department = data.get("department", "").strip()
    user_role = data.get("user_role", "").strip()
    password = data.get("password")
    confirm_password = data.get("confirm_password")
    
    # Validation
    if not all([user_id, full_name, email, phone_number, department, user_role, password, confirm_password]):
        return jsonify({"error": "All fields are required"}), 400
        
    if not is_valid_email(email):
        return jsonify({"error": "Invalid email address format"}), 400
        
    if password != confirm_password:
        return jsonify({"error": "Passwords do not match"}), 400
        
    if not check_password_complexity(password):
        return jsonify({"error": "Password does not meet complexity requirements"}), 400
        
    if user_role not in ["Supervisor", "Inventory Inspector", "Worker"]:
        return jsonify({"error": "Invalid user role selection"}), 400
        
    # Check ID uniqueness
    with get_db_cursor() as cur:
        # Check active users
        cur.execute("SELECT user_id FROM users WHERE user_id = %s", (user_id,))
        if cur.fetchone():
            return jsonify({"error": "User ID already exists"}), 409
            
        # Check pending registration payloads
        cur.execute("""
            SELECT payload FROM email_verification 
            WHERE purpose = 'Registration' AND expiry_time > NOW()
        """)
        rows = cur.fetchall()
        for row in rows:
            payload_str = row.get("payload")
            if payload_str:
                try:
                    payload = json.loads(payload_str)
                    if payload.get("user_id") == user_id:
                        return jsonify({"error": "User ID already exists"}), 409
                except Exception:
                    pass

    # Check if email is already taken in Users
    with get_db_cursor() as cur:
        cur.execute("SELECT user_id FROM users WHERE email = %s", (email,))
        if cur.fetchone():
            return jsonify({"error": "Email is already registered"}), 409
            
    print("User validated", flush=True)
    
    # Process Registration
    hashed_pwd = hash_password(password)
    print("Generating OTP...", flush=True)
    otp = f"{random.randint(100000, 999999)}"
    print(f"OTP Generated : {otp}", flush=True)
    
    expiry_time = datetime.datetime.now() + datetime.timedelta(minutes=10)
    
    payload = {
        "user_id": user_id,
        "password": hashed_pwd,
        "user_role": user_role,
        "full_name": full_name,
        "username": username,
        "email": email,
        "phone_number": phone_number,
        "department": department
    }
    
    print("Saving OTP...", flush=True)
    with get_db_cursor(commit=True) as cur:
        # Delete old registration attempts for this email
        cur.execute("DELETE FROM email_verification WHERE email = %s AND purpose = 'Registration'", (email,))
        # Insert OTP + registration payload
        cur.execute("""
            INSERT INTO email_verification (email, otp, expiry_time, purpose, payload)
            VALUES (%s, %s, %s, 'Registration', %s)
        """, (email, otp, expiry_time, json.dumps(payload)))
    
    print("OTP Saved", flush=True)
    
    # Send email
    send_otp_email(email, otp, "Registration")
    
    print("Verification page returned", flush=True)
    return jsonify({"message": "Registration successful. OTP sent to email."}), 200


@auth_extended_bp.route("/api/send-registration-otp", methods=["POST"])
def send_registration_otp():
    print("Resend registration OTP request received", flush=True)
    data = request.get_json(silent=True) or {}
    email = data.get("email", "").strip()
    
    if not email:
        return jsonify({"error": "Email address is required"}), 400
        
    print("Saving OTP...", flush=True)
    with get_db_cursor(commit=True) as cur:
        cur.execute("""
            SELECT id, payload FROM email_verification 
            WHERE email = %s AND purpose = 'Registration'
        """, (email,))
        row = cur.fetchone()
        
        if not row:
            return jsonify({"error": "No registration session found for this email. Please register again."}), 404
            
        print("Generating OTP...", flush=True)
        otp = f"{random.randint(100000, 999999)}"
        print(f"OTP Generated : {otp}", flush=True)
        
        expiry_time = datetime.datetime.now() + datetime.timedelta(minutes=10)
        
        cur.execute("""
            UPDATE email_verification 
            SET otp = %s, expiry_time = %s 
            WHERE id = %s
        """, (otp, expiry_time, row["id"]))
        
    print("OTP Saved", flush=True)
    send_otp_email(email, otp, "Registration")
    print("Verification page returned", flush=True)
    return jsonify({"message": "Verification code resent successfully"}), 200

@auth_extended_bp.route("/api/verify-registration", methods=["POST"])
def verify_registration():
    print("Verify registration OTP request received", flush=True)
    data = request.get_json(silent=True) or {}
    email = data.get("email", "").strip()
    otp = data.get("otp", "").strip()
    
    if not email or not otp:
        return jsonify({"error": "Email and verification code are required"}), 400
        
    with get_db_cursor(commit=True) as cur:
        cur.execute("""
            SELECT id, otp, expiry_time, payload FROM email_verification 
            WHERE email = %s AND purpose = 'Registration'
        """, (email,))
        row = cur.fetchone()
        
        if not row:
            print("Verification failed: No registration record found", flush=True)
            return jsonify({"error": "No registration record found for this email"}), 404
            
        if row["otp"] != otp:
            print("Verification failed: Invalid verification code", flush=True)
            return jsonify({"error": "Invalid verification code"}), 400
            
        # Check expiry
        if row["expiry_time"] < datetime.datetime.now():
            print("Verification failed: Verification code has expired", flush=True)
            return jsonify({"error": "Verification code has expired. Please resend code."}), 400
            
        # Verified, insert user
        try:
            payload = json.loads(row["payload"])
            cur.execute("""
                INSERT INTO users (user_id, password, user_role, full_name, username, email, phone_number, department, email_verified)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 1)
            """, (
                payload["user_id"],
                payload["password"],
                payload["user_role"],
                payload["full_name"],
                payload["username"],
                payload["email"],
                payload["phone_number"],
                payload["department"]
            ))
            
            # Clean up verification entry
            cur.execute("DELETE FROM email_verification WHERE email = %s", (email,))
            print("User verification completed successfully. User inserted to database.", flush=True)
            
        except Exception as e:
            print("Failed to complete user registration. Exception details:")
            import traceback
            traceback.print_exc()
            return jsonify({"error": f"Failed to complete user registration: {str(e)}"}), 500
            
    return jsonify({"message": "Email verified successfully! You can now log in."}), 200


@auth_extended_bp.route("/api/send-reset-otp", methods=["POST"])
def send_reset_otp():
    print("Forgot password request received", flush=True)
    data = request.get_json(silent=True) or {}
    email = data.get("email", "").strip()
    
    if not email:
        return jsonify({"error": "Email is required"}), 400
        
    with get_db_cursor(commit=True) as cur:
        # Check if email exists in Users
        cur.execute("SELECT user_id FROM users WHERE email = %s", (email,))
        user = cur.fetchone()
        if not user:
            print("Forgot password validation failed: Email not found in users table", flush=True)
            return jsonify({"error": "Email is not associated with any account"}), 404
            
        print("User validated", flush=True)
        print("Generating OTP...", flush=True)
        otp = f"{random.randint(100000, 999999)}"
        print(f"OTP Generated : {otp}", flush=True)
        
        expiry_time = datetime.datetime.now() + datetime.timedelta(minutes=10)
        
        print("Saving OTP...", flush=True)
        # Delete old reset OTPs
        cur.execute("DELETE FROM email_verification WHERE email = %s AND purpose = 'Password Reset'", (email,))
        
        # Save new reset OTP
        cur.execute("""
            INSERT INTO email_verification (email, otp, expiry_time, purpose)
            VALUES (%s, %s, %s, 'Password Reset')
        """, (email, otp, expiry_time))
        
    print("OTP Saved", flush=True)
    send_otp_email(email, otp, "Password Reset")
    print("Reset password page returned", flush=True)
    return jsonify({"message": "Password reset code sent to email"}), 200

@auth_extended_bp.route("/api/reset-password", methods=["POST"])
def reset_password():
    print("Reset password request received", flush=True)
    data = request.get_json(silent=True) or {}
    email = data.get("email", "").strip()
    otp = data.get("otp", "").strip()
    password = data.get("password")
    confirm_password = data.get("confirm_password")
    
    if not all([email, otp, password, confirm_password]):
        return jsonify({"error": "All fields are required"}), 400
        
    if password != confirm_password:
        return jsonify({"error": "Passwords do not match"}), 400
        
    if not check_password_complexity(password):
        return jsonify({"error": "Password does not meet complexity requirements"}), 400
        
    with get_db_cursor(commit=True) as cur:
        cur.execute("""
            SELECT id, otp, expiry_time FROM email_verification 
            WHERE email = %s AND purpose = 'Password Reset'
        """, (email,))
        row = cur.fetchone()
        
        if not row:
            print("Reset password failed: Invalid or expired session", flush=True)
            return jsonify({"error": "Invalid or expired password reset session"}), 404
            
        if row["otp"] != otp:
            print("Reset password failed: Invalid verification code", flush=True)
            return jsonify({"error": "Invalid verification code"}), 400
            
        if row["expiry_time"] < datetime.datetime.now():
            print("Reset password failed: Verification code has expired", flush=True)
            return jsonify({"error": "Verification code has expired"}), 400
            
        # Update user password
        hashed_pwd = hash_password(password)
        cur.execute("UPDATE users SET password = %s WHERE email = %s", (hashed_pwd, email))
        
        # Clean up verification entry
        cur.execute("DELETE FROM email_verification WHERE email = %s", (email,))
        
    print("Password reset successfully. Password updated in database.", flush=True)
    return jsonify({"message": "Password reset successful! You can now log in."}), 200

