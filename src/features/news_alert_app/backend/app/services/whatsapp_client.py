from __future__ import annotations

import httpx

from app.core.config import settings


def _build_whatsapp_url() -> str:
    phone_number_id = (settings.whatsapp_phone_number_id or "").strip()
    if not phone_number_id:
        raise RuntimeError("Missing WHATSAPP_PHONE_NUMBER_ID")
    version = (settings.whatsapp_graph_api_version or "v23.0").strip()
    return f"https://graph.facebook.com/{version}/{phone_number_id}/messages"


def send_whatsapp_text(*, to_phone: str, body: str) -> dict:
    token = (settings.whatsapp_access_token or "").strip()
    if not token:
        raise RuntimeError("Missing WHATSAPP_ACCESS_TOKEN")

    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": to_phone,
        "type": "text",
        "text": {"body": body},
    }
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    url = _build_whatsapp_url()

    with httpx.Client(timeout=20.0) as client:
        response = client.post(url, headers=headers, json=payload)
        data = response.json() if response.content else {}
        if response.status_code >= 400:
            raise RuntimeError(f"WhatsApp API error {response.status_code}: {data}")
        return data
