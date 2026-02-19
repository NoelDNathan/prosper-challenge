"""
Get the OTP code from the email.
"""
import imaplib
import email
import re
import time
import os

from dotenv import load_dotenv
load_dotenv()

IMAP_HOST = "imap.gmail.com"
EMAIL_ACCOUNT = os.environ.get("MAIL_EMAIL")
EMAIL_PASSWORD = os.environ.get("MAIL_PASSWORD")


def _digits_in_text(text):
    """
    Extract the OTP code from the text.
    Args:
        text: The text to extract the OTP code from.
    Returns:
        The OTP code.
    """
    # Avoid matching #colors in css because they are used to style the text
    return re.findall(r"(?<!#)\b\d{6}\b", text or "")


def extract_otp_from_message(msg):
    """
    Extract the OTP code from the email message.
    Args:
        msg: The email message.
    Returns:
        The OTP code.
    """
    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            payload = part.get_payload(decode=True)
            if not payload:
                continue
            body = payload.decode(errors="ignore") if isinstance(payload, bytes) else payload
            if content_type == "text/plain":
                match = _digits_in_text(body)
                if match:
                    return match[0]
            if content_type == "text/html":
                match = re.search(r"<h2[^>]*>\s*(\d{6})\s*</h2>", body, re.IGNORECASE)
                if match:
                    return match.group(1)
                match = re.search(r">\s*(\d{6})\s*<", body)
                if match:
                    return match.group(1)
    else:
        payload = msg.get_payload(decode=True)
        body = payload.decode(errors="ignore") if isinstance(payload, bytes) else payload
        match = _digits_in_text(body)
        if match:
            return match[0]
    return None

def print_email_body(msg):
    """
    Print the raw payload body of an email message.
    """
    payload = msg.get_payload(decode=True)
    if isinstance(payload, bytes):
        body = payload.decode(errors="ignore")
    else:
        body = payload
    print("Raw payload body:", body)

def get_otp(timeout=30, sender_filter=None, subject_filter=None, debug=False):
    """
    Get the OTP code from the email.
    Args:
        timeout: The timeout in seconds.
        sender_filter: The sender of the email.
        subject_filter: The subject of the email.
        debug: Whether to print the email body.
    Returns:
        The OTP code.
    """
    mail = imaplib.IMAP4_SSL(IMAP_HOST)
    mail.login(EMAIL_ACCOUNT, EMAIL_PASSWORD)
    mail.select("INBOX")

    start_time = time.time()

    while time.time() - start_time < timeout:
        criteria = ['UNSEEN']

        if sender_filter:
            criteria += ['FROM', f'"{sender_filter}"']

        if subject_filter:
            criteria += ['SUBJECT', f'"{subject_filter}"']

        status, messages = mail.search(None, *criteria)

        if status == "OK":
            mail_ids = messages[0].split()

            if mail_ids:
                latest_id = mail_ids[-1]

                status, msg_data = mail.fetch(latest_id, "(RFC822)")
                if status == "OK":
                    raw_email = msg_data[0][1]
                    msg = email.message_from_bytes(raw_email)
                    
                    if debug:
                        print_email_body(msg)
            
                    otp = extract_otp_from_message(msg)
                    if otp:
                        mail.logout()
                        return otp

        time.sleep(0.5)

    mail.logout()
    raise TimeoutError("OTP email not received")
