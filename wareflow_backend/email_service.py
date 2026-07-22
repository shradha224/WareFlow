import sib_api_v3_sdk
from sib_api_v3_sdk.rest import ApiException
import os

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

    api_key = os.getenv("BREVO_API_KEY")
    sender_email = os.getenv("BREVO_SENDER_EMAIL")

    if not api_key:
        print("BREVO ERROR : BREVO_API_KEY not configured in environment variables", flush=True)
        _print_debug_otp(to_email, otp)
        return True

    if not sender_email:
        print("BREVO ERROR : BREVO_SENDER_EMAIL not configured in environment variables", flush=True)
        _print_debug_otp(to_email, otp)
        return True

    print("Sending OTP through Brevo...", flush=True)
    try:
        # Configure API key authorization: api-key
        configuration = sib_api_v3_sdk.Configuration()
        configuration.api_key['api-key'] = api_key

        api_instance = sib_api_v3_sdk.TransactionalEmailsApi(sib_api_v3_sdk.ApiClient(configuration))

        # Define email details
        sender = {"name": "WareFlow", "email": sender_email}
        to = [{"email": to_email}]
        send_smtp_email = sib_api_v3_sdk.SendSmtpEmail(
            to=to,
            sender=sender,
            subject=subject,
            html_content=html_body
        )

        api_response = api_instance.send_transac_email(send_smtp_email)
        print(f"Email delivered successfully. Response: {api_response}", flush=True)
        return True
        
    except ApiException as e:
        print(f"Brevo Error: {e}", flush=True)
        _print_debug_otp(to_email, otp)
        return False
    except Exception as e:
        print(f"Unexpected Brevo Error: {e}", flush=True)
        _print_debug_otp(to_email, otp)
        return False

def _print_debug_otp(email: str, otp: str):
    print("DEBUG OTP", flush=True)
    print(otp, flush=True)
