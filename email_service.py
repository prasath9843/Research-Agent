import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional

SMTP_SERVER = os.getenv("SMTP_SERVER", "")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASS = os.getenv("SMTP_PASS", "")
SMTP_FROM = os.getenv("SMTP_FROM", os.getenv("SMTP_USER", "noreply@deepresearch.studio"))

def is_smtp_configured() -> bool:
    return bool(SMTP_SERVER and SMTP_USER and SMTP_PASS)

def send_email(to_email: str, subject: str, html_content: str, text_content: Optional[str] = None) -> bool:
    if not is_smtp_configured():
        print(f"\n[EMAIL SIMULATION] To: {to_email} | Subject: {subject}")
        if text_content:
            print(f"[EMAIL CONTENT]\n{text_content}\n")
        return True

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"DeepResearch Studio <{SMTP_FROM}>"
        msg["To"] = to_email

        if text_content:
            msg.attach(MIMEText(text_content, "plain"))
        msg.attach(MIMEText(html_content, "html"))

        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=10) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASS)
            server.sendmail(SMTP_FROM, [to_email], msg.as_string())
        print(f"[EMAIL SENT] Successfully dispatched email to {to_email}")
        return True
    except Exception as e:
        print(f"[EMAIL ERROR] Failed to send email to {to_email}: {e}")
        return False

def send_verification_otp_email(to_email: str, name: str, otp_code: str, expiry_minutes: int = 10) -> bool:
    display_name = name or "Researcher"
    subject = f"{otp_code} is your DeepResearch Studio verification code"
    text_body = f"Hello {display_name},\n\nYour 6-digit verification code is: {otp_code}\n\nThis code will expire in {expiry_minutes} minutes.\n\nBest regards,\nDeepResearch Studio Security Team"
    html_body = f"""<!DOCTYPE html><html><body style='background:#090d16;color:#e2e8f0;font-family:sans-serif;padding:20px;'><div style='max-width:500px;margin:auto;background:#0f172a;border:1px solid #1e293b;border-radius:14px;padding:28px;'><h2 style='color:#10b981;margin-top:0;'>Verify Your Email Address</h2><p>Hello <strong>{display_name}</strong>,</p><p>Please enter your 6-digit verification code to activate your private research workspace:</p><div style='background:#1e293b;border:2px dashed #10b981;border-radius:10px;padding:16px;text-align:center;margin:20px 0;'><h1 style='font-size:36px;letter-spacing:8px;color:#10b981;margin:0;'>{otp_code}</h1><small style='color:#64748b;'>Expires in {expiry_minutes} minutes &bull; Single-use only</small></div><p style='font-size:12px;color:#64748b;'>If you did not request this, you can safely ignore this email.</p></div></body></html>"""
    return send_email(to_email, subject, html_body, text_body)

def send_password_reset_email(to_email: str, name: str, reset_code: str, expiry_minutes: int = 10) -> bool:
    display_name = name or "Researcher"
    subject = f"{reset_code} is your DeepResearch password reset code"
    text_body = f"Hello {display_name},\n\nYour 6-digit password reset code is: {reset_code}\n\nThis code will expire in {expiry_minutes} minutes.\n\nBest regards,\nDeepResearch Studio Security Team"
    html_body = f"""<!DOCTYPE html><html><body style='background:#090d16;color:#e2e8f0;font-family:sans-serif;padding:20px;'><div style='max-width:500px;margin:auto;background:#0f172a;border:1px solid #1e293b;border-radius:14px;padding:28px;'><h2 style='color:#ef4444;margin-top:0;'>Reset Your Password</h2><p>Hello <strong>{display_name}</strong>,</p><p>We received a request to reset your password. Use this 6-digit code:</p><div style='background:#1e293b;border:2px dashed #ef4444;border-radius:10px;padding:16px;text-align:center;margin:20px 0;'><h1 style='font-size:36px;letter-spacing:8px;color:#ef4444;margin:0;'>{reset_code}</h1><small style='color:#64748b;'>Expires in {expiry_minutes} minutes &bull; Single-use only</small></div><p style='font-size:12px;color:#64748b;'>If you did not request a password reset, your password remains unchanged.</p></div></body></html>"""
    return send_email(to_email, subject, html_body, text_body)
