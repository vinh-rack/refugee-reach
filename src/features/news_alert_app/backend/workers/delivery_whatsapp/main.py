from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path
import sys
import uuid

# Allow running this file directly: `python workers/delivery_whatsapp/main.py`
BACKEND_DIR = Path(__file__).resolve().parents[2]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from sqlalchemy.orm import joinedload

from app.db.session import SessionLocal
from app.core.config import settings
from app.models.alert import Alert
from app.models.delivery import Delivery
from app.models.enums import DeliveryChannel, DeliveryStatus
from app.models.user_preference import UserPreference
from app.queue.constant import DELIVERY_WHATSAPP_QUEUE
from app.queue.rabbitmq import consumer
from app.services.whatsapp_client import send_whatsapp_text


def _parse_uuid(value: str | None) -> uuid.UUID | None:
    if not value:
        return None
    try:
        return uuid.UUID(str(value))
    except ValueError:
        return None


def _build_message(delivery: Delivery, alert: Alert) -> str:
    event = alert.event
    summary = ""
    if isinstance(alert.analysis_snapshot, dict):
        summary = (alert.analysis_snapshot.get("summary") or "").strip()
    if not summary:
        summary = (event.latest_summary or "").strip()
    summary = summary[:700] if summary else "No summary available."

    topic = event.topic or "unknown"
    region = event.region or "unknown"
    app_base_url = (settings.app_base_url or "").strip().rstrip("/")
    event_link = f"{app_base_url}/events/{event.id}" if app_base_url else f"/events/{event.id}"
    return (
        f"[{alert.alert_level.value.upper()}] RefugeeReach Alert\n"
        f"Event: {event.canonical_title}\n"
        f"Topic: {topic} | Region: {region}\n"
        f"Summary: {summary}\n"
        f"Read more: {event_link}"
    )


def process_delivery(delivery_id: uuid.UUID) -> str:
    db = SessionLocal()
    try:
        delivery = (
            db.query(Delivery)
            .options(joinedload(Delivery.alert).joinedload(Alert.event))
            .filter(Delivery.id == delivery_id)
            .first()
        )
        if not delivery:
            print(f"[delivery_whatsapp] delivery not found: {delivery_id}")
            return "missing"

        if delivery.channel != DeliveryChannel.WHATSAPP:
            print(f"[delivery_whatsapp] skipping non-whatsapp delivery={delivery.id} channel={delivery.channel}")
            return "skipped"

        if delivery.status == DeliveryStatus.SENT:
            print(f"[delivery_whatsapp] already sent delivery={delivery.id}")
            return "already_sent"

        # Load related user preference by destination for policy audit/debug visibility.
        pref = (
            db.query(UserPreference)
            .filter(UserPreference.whatsapp_phone == delivery.destination)
            .first()
        )

        message = _build_message(delivery, delivery.alert)
        delivery.attempt_count = (delivery.attempt_count or 0) + 1

        try:
            response_payload = send_whatsapp_text(
                to_phone=delivery.destination,
                body=message,
            )
            delivery.status = DeliveryStatus.SENT
            delivery.sent_at = datetime.now(timezone.utc)
            delivery.error_message = None
            delivery.response_payload = response_payload

            provider_message_id = None
            if isinstance(response_payload, dict):
                messages = response_payload.get("messages")
                if isinstance(messages, list) and messages:
                    first = messages[0]
                    if isinstance(first, dict):
                        provider_message_id = first.get("id")
            delivery.provider_message_id = provider_message_id
            db.commit()

            user_info = str(pref.user_id) if pref else "unknown_user"
            print(
                f"[delivery_whatsapp] sent delivery={delivery.id} "
                f"user={user_info} provider_message_id={provider_message_id}"
            )
            return "sent"
        except Exception as exc:
            delivery.status = DeliveryStatus.FAILED
            delivery.error_message = str(exc)[:2000]
            delivery.response_payload = {"error": str(exc)}
            db.commit()
            print(f"[delivery_whatsapp] failed delivery={delivery.id}: {exc}")
            return "failed"
    except Exception as exc:
        db.rollback()
        print(f"[delivery_whatsapp] crash delivery={delivery_id}: {exc}")
        raise
    finally:
        db.close()


def handle_delivery_message(payload: dict):
    delivery_id = _parse_uuid(payload.get("delivery_id"))
    if not delivery_id:
        print(f"[delivery_whatsapp] payload missing delivery_id: {payload}")
        return
    process_delivery(delivery_id)


def run_consumer():
    print(f"[delivery_whatsapp] consuming from {DELIVERY_WHATSAPP_QUEUE}")
    consumer(DELIVERY_WHATSAPP_QUEUE, handle_delivery_message)


def run_backfill(limit: int):
    db = SessionLocal()
    try:
        rows = (
            db.query(Delivery.id)
            .filter(
                Delivery.channel == DeliveryChannel.WHATSAPP,
                Delivery.status.in_([DeliveryStatus.PENDING, DeliveryStatus.RETRYING]),
            )
            .order_by(Delivery.created_at.asc())
            .limit(limit)
            .all()
        )
        delivery_ids = [row[0] for row in rows]
    finally:
        db.close()

    print(f"[delivery_whatsapp] backfill candidates={len(delivery_ids)}")
    counts = {"sent": 0, "failed": 0, "missing": 0, "skipped": 0, "already_sent": 0}
    for delivery_id in delivery_ids:
        result = process_delivery(delivery_id)
        if result in counts:
            counts[result] += 1
    print(f"[delivery_whatsapp] backfill completed {counts}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="WhatsApp delivery worker.")
    parser.add_argument(
        "--backfill",
        action="store_true",
        help="Process pending WhatsApp deliveries from DB instead of consuming queue.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=200,
        help="Maximum number of pending deliveries in backfill mode.",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    if args.backfill:
        run_backfill(limit=args.limit)
    else:
        run_consumer()


if __name__ == "__main__":
    main()
