"""Send password reset links via Resend when configured; otherwise log for local dev."""
import html
import logging
import os

import resend

logger = logging.getLogger(__name__)


def send_password_reset_email(to_email: str, reset_url: str) -> None:
    api_key = os.getenv("RESEND_API_KEY", "").strip()
    if not api_key:
        logger.warning(
            "Password reset link for %s (set RESEND_API_KEY to email users): %s",
            to_email,
            reset_url,
        )
        return

    resend.api_key = api_key
    from_addr = os.getenv("EMAIL_FROM", "noreply@nellits.com").strip()
    app_name = os.getenv("APP_NAME", "Nellits")

    resend.Emails.send({
        "from": from_addr,
        "to": [to_email],
        "subject": f"Reset your {app_name} password",
        "html": (
            f"<p>You requested a password reset for {html.escape(app_name)}.</p>"
            f'<p><a href="{html.escape(reset_url, quote=True)}">Click here to choose a new password</a> '
            f"(expires in one hour).</p>"
            f"<p>If you did not request this, you can ignore this email.</p>"
        ),
    })
