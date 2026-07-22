import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os

def send_otp_email(to_email: str, otp: str, purpose: str) -> bool:
    print("send_email() called", flush=True)
    print(f"Sending email to: {to_email}", flush=True)

    subject = "WareFlow OTP Verification"
    
    # HTML formatted email body
    html_body = f"""
    <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #ddd; border-radius: 10px;">
                <div style="text-align: center; margin-bottom: 20px;">
                    <h2 style="color: #2367C1; margin: 0;">WareFlow</h2>
                    <p style="font-size: 14px; color: #666; margin: 5px 0 0 0;">Future-Proof Manufacturing Systems</p>
                </div>
                <hr style="border: 0; border-top: 1px solid #eee;" />
                <p>Hello,</p>
                <p>You have requested a verification code for <strong>{purpose}</strong> on the WareFlow platform.</p>
                <div style="text-align: center; margin: 30px 0;">
                    <span style="font-size: 32px; font-weight: bold; letter-spacing: 5px; color: #2367C1; background-color: #f0f4fa; padding: 10px 20px; border-radius: 5px; border: 1px dashed #2367C1;">
                        {otp}
                    </span>
                </div>
                <p>This code is valid for <strong>10 minutes</strong>. If you did not request this code, please ignore this email.</p>
                <hr style="border: 0; border-top: 1px solid #eee; margin-top: 30px;" />
                <p style="font-size: 12px; color: #999; text-align: center;">
                    This is an automated message. Please do not reply directly to this email.
                </p>
            </div>
        </body>
    </html>
    """
    
    text_body = f"Hello,\n\nYour WareFlow {purpose} verification code is: {otp}\n\nThis code is valid for 10 minutes."

    smtp_host = os.getenv("SMTP_HOST")
    smtp_port_str = os.getenv("SMTP_PORT")
    smtp_email = os.getenv("SMTP_EMAIL")
    smtp_password = os.getenv("SMTP_PASSWORD")

    if not smtp_host or not smtp_port_str or not smtp_email or not smtp_password:
        print("SMTP ERROR: SMTP credentials not configured in environment variables", flush=True)
        _print_debug_otp(to_email, otp)
        return True

    try:
        smtp_port = int(smtp_port_str)
    except ValueError as e:
        print(f"SMTP ERROR: Invalid SMTP_PORT '{smtp_port_str}': {e}", flush=True)
        _print_debug_otp(to_email, otp)
        return False

    print("Connecting SMTP...", flush=True)
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = smtp_email
        msg["To"] = to_email

        # Attach text and HTML versions
        msg.attach(MIMEText(text_body, "plain"))
        msg.attach(MIMEText(html_body, "html"))

        # Connection setup
        if smtp_port == 465:
            server = smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=10)
        else:
            server = smtplib.SMTP(smtp_host, smtp_port, timeout=10)
            server.starttls()
            
        server.login(smtp_email, smtp_password)
        print("SMTP Login Successful", flush=True)
        
        print("Sending Email...", flush=True)
        server.sendmail(smtp_email, to_email, msg.as_string())
        server.quit()
        
        print("Email Sent Successfully", flush=True)
        return True
        
    except Exception as e:
        print(f"SMTP ERROR: {e}", flush=True)
        _print_debug_otp(to_email, otp)
        return False

def _print_debug_otp(email: str, otp: str):
    print("DEBUG OTP", flush=True)
    print(otp, flush=True)
