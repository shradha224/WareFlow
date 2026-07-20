import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from config import Config

def send_otp_email(to_email: str, otp: str, purpose: str) -> bool:
    print("send_email() called", flush=True)
    print(f"Sending email to : {to_email}", flush=True)
    print(f"SMTP USER: {Config.SMTP_USER}", flush=True)
    print(f"SMTP HOST: {Config.SMTP_HOST}", flush=True)
    print(f"SMTP PORT: {Config.SMTP_PORT}", flush=True)

    subject = f"WareFlow - {purpose} OTP Verification"
    
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

    if not Config.SMTP_USER or not Config.SMTP_PASSWORD:
        print("SMTP ERROR : SMTP credentials not configured in environment variables", flush=True)
        _print_debug_otp(to_email, otp)
        return True

    print("Connecting SMTP...", flush=True)
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = Config.SMTP_FROM_EMAIL
        msg["To"] = to_email

        # Attach text and HTML versions
        msg.attach(MIMEText(text_body, "plain"))
        msg.attach(MIMEText(html_body, "html"))

        # Smart connection based on port
        if Config.SMTP_PORT == 465:
            server = smtplib.SMTP_SSL(Config.SMTP_HOST, Config.SMTP_PORT, timeout=10)
        else:
            server = smtplib.SMTP(Config.SMTP_HOST, Config.SMTP_PORT, timeout=10)
            if Config.SMTP_PORT == 587:
                server.starttls()
            
        print("SMTP Connected", flush=True)
        server.login(Config.SMTP_USER, Config.SMTP_PASSWORD)
        
        print("Sending email...", flush=True)
        server.sendmail(Config.SMTP_FROM_EMAIL, to_email, msg.as_string())
        server.quit()
        
        print("Email Sent Successfully", flush=True)
        return True
        
    except Exception as e:
        print(f"SMTP ERROR : {e}", flush=True)
        _print_debug_otp(to_email, otp)
        return False

def _print_debug_otp(email: str, otp: str):
    print("DEBUG OTP", flush=True)
    print(otp, flush=True)


