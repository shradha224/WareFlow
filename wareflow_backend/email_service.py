import resend
import os

resend.api_key = os.getenv("RESEND_API_KEY")

def send_otp_email(to_email: str, otp: str, purpose: str) -> bool:
    print("send_email() called", flush=True)
    print(f"Sending email to : {to_email}", flush=True)

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

    if not resend.api_key:
        print("RESEND ERROR : RESEND_API_KEY not configured in environment variables", flush=True)
        _print_debug_otp(to_email, otp)
        return True

    print("Sending email via Resend API...", flush=True)
    try:
        r = resend.Emails.send({
            "from": "WareFlow <onboarding@resend.dev>",
            "to": to_email,
            "subject": subject,
            "html": html_body
        })
        print(f"Email Sent Successfully, Resend Response: {r}", flush=True)
        return True
        
    except Exception as e:
        print(f"RESEND ERROR : {e}", flush=True)
        _print_debug_otp(to_email, otp)
        return False

def _print_debug_otp(email: str, otp: str):
    print("DEBUG OTP", flush=True)
    print(otp, flush=True)
