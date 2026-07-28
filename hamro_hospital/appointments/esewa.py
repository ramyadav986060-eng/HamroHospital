"""
eSewa ePay v2 integration helpers.

This implements the standard eSewa ePay v2 flow:
  1. Build a signed form (HMAC-SHA256 over a fixed field set) and auto-submit
     it to eSewa's payment page.
  2. eSewa redirects back to our success_url with a base64-encoded JSON
     payload in ?data=... ; we decode it, verify its signature, and confirm
     status == "COMPLETE" before crediting the appointment.

NOTE: eSewa's exact endpoint paths and required fields can change over time -
double-check against eSewa's current merchant documentation before going live.
This module isolates all of that detail in one place so updating it later
means touching only this file, not the views that call it.
"""
import base64
import hashlib
import hmac
import json

from django.conf import settings

ESEWA_SANDBOX_FORM_URL = 'https://rc-epay.esewa.com.np/api/epay/main/v2/form'
ESEWA_LIVE_FORM_URL = 'https://epay.esewa.com.np/api/epay/main/v2/form'

# Fields that are signed together, in this exact order, per eSewa's spec.
SIGNED_FIELD_NAMES = 'total_amount,transaction_uuid,product_code'


def get_form_url():
    return ESEWA_SANDBOX_FORM_URL if settings.ESEWA_SANDBOX else ESEWA_LIVE_FORM_URL


def _sign(message: str) -> str:
    secret = settings.ESEWA_SECRET_KEY.encode('utf-8')
    digest = hmac.new(secret, message.encode('utf-8'), hashlib.sha256).digest()
    return base64.b64encode(digest).decode('utf-8')


def build_payment_fields(*, amount, transaction_uuid, success_url, failure_url):
    """
    Returns the full dict of hidden form fields to POST to eSewa's form_url.
    `amount` and `total_amount` are equal here since we don't charge any
    separate tax/service fee on top of the registration fee.
    """
    amount_str = f"{amount:.2f}"
    message = f"total_amount={amount_str},transaction_uuid={transaction_uuid},product_code={settings.ESEWA_MERCHANT_CODE}"
    signature = _sign(message)

    return {
        'amount': amount_str,
        'tax_amount': '0',
        'total_amount': amount_str,
        'transaction_uuid': str(transaction_uuid),
        'product_code': settings.ESEWA_MERCHANT_CODE,
        'product_service_charge': '0',
        'product_delivery_charge': '0',
        'success_url': success_url,
        'failure_url': failure_url,
        'signed_field_names': SIGNED_FIELD_NAMES,
        'signature': signature,
    }


def decode_and_verify_response(data_param: str):
    """
    Decodes the base64 `data` query parameter eSewa appends to success_url
    and verifies its signature. Returns the parsed dict on success, or None
    if decoding/signature verification fails.
    """
    try:
        decoded = base64.b64decode(data_param).decode('utf-8')
        payload = json.loads(decoded)
    except (ValueError, UnicodeDecodeError, json.JSONDecodeError):
        return None

    signed_field_names = payload.get('signed_field_names', '')
    fields = signed_field_names.split(',')
    try:
        message = ','.join(f"{field}={payload[field]}" for field in fields)
    except KeyError:
        return None

    expected_signature = _sign(message)
    if not hmac.compare_digest(expected_signature, payload.get('signature', '')):
        return None

    return payload
