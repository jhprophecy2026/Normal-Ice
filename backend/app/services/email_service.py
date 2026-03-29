"""
Email service — sends formal TPA emails via Resend API.
If RESEND_API_KEY is not configured, emails are logged to console instead.
"""
import logging

from app.config import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# TPA name → email mapping (demo values — replace with real TPA emails)
# ---------------------------------------------------------------------------
_TPA_EMAILS: dict[str, str] = {
    "medi assist":        "claims@mediassist.in",
    "max bupa tpa":       "preauth@maxbuppa.com",
    "max bupa":           "preauth@maxbuppa.com",
    "star tpa":           "cashless@starhealth.in",
    "star health":        "cashless@starhealth.in",
    "health india tpa":   "claims@healthindia.co.in",
    "health india":       "claims@healthindia.co.in",
    "fhpl":               "preauth@fhpl.net",
    "paramount tpa":      "auth@paramounttpa.com",
    "vidal health":       "cashless@vidalhealth.in",
    "nha":                "claims@nha.gov.in",
}


def get_tpa_email(tpa_name: str | None) -> str:
    if not tpa_name:
        return settings.DEFAULT_TPA_EMAIL
    return _TPA_EMAILS.get(tpa_name.strip().lower(), settings.DEFAULT_TPA_EMAIL)


def send_email(to: str, subject: str, html: str) -> bool:
    """
    Send an HTML email via Resend. Returns True on success, False on failure.
    If RESEND_API_KEY is not configured, logs the email and returns False gracefully.
    """
    if not settings.RESEND_API_KEY:
        logger.info(
            "\n" + "=" * 60 +
            f"\n[EMAIL — Resend not configured, not sent]"
            f"\nTo:      {to}"
            f"\nSubject: {subject}"
            "\n" + "=" * 60
        )
        return False

    try:
        import resend
        resend.api_key = settings.RESEND_API_KEY

        resend.Emails.send({
            "from": settings.FROM_EMAIL,
            "to": [to],
            "subject": subject,
            "html": html,
        })

        logger.info(f"Email sent via Resend → {to} | {subject}")
        return True

    except Exception as exc:
        logger.error(f"Resend email failed ({to}): {exc}")
        return False
