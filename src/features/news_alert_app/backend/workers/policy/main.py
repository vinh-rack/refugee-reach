from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path
import sys
import uuid

# Allow running this file directly: `python workers/policy/main.py`
BACKEND_DIR = Path(__file__).resolve().parents[2]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from sqlalchemy.orm import joinedload

from app.db.session import SessionLocal
from app.models.alert import Alert
from app.models.analysis import Analysis
from app.models.delivery import Delivery
from app.models.enums import AlertLevel, DeliveryChannel, DeliveryStatus
from app.models.user import User
from app.models.user_preference import UserPreference
from app.queue.constant import (
    ANALYSIS_RESULT_QUEUE,
    DELIVERY_TELEGRAM_QUEUE,
    DELIVERY_WHATSAPP_QUEUE,
)
from app.queue.rabbitmq import consumer, publish


CRITICAL_SEVERITY_THRESHOLD = 0.85
CRITICAL_CONFIDENCE_THRESHOLD = 0.9


def _parse_uuid(value: str | None) -> uuid.UUID | None:
    if not value:
        return None
    try:
        return uuid.UUID(str(value))
    except ValueError:
        return None


def should_create_critical_alert(analysis: Analysis) -> bool:
    return (
        (analysis.severity_score or 0.0) >= CRITICAL_SEVERITY_THRESHOLD
        and (analysis.confidence_score or 0.0) >= CRITICAL_CONFIDENCE_THRESHOLD
    )


def find_telegram_recipients(db, analysis: Analysis) -> list[UserPreference]:
    event = analysis.event

    prefs = (
        db.query(UserPreference)
        .join(User, User.id == UserPreference.user_id)
        .filter(
            User.is_active == True,
            UserPreference.telegram_enabled == True,
            UserPreference.telegram_chat_id.isnot(None),
            UserPreference.min_severity <= analysis.severity_score,
        )
        .all()
    )

    recipients: list[UserPreference] = []
    for pref in prefs:
        if pref.topics and event.topic and event.topic not in pref.topics:
            continue
        if pref.regions and event.region and event.region not in pref.regions:
            continue
        recipients.append(pref)
    return recipients


def find_whatsapp_recipients(db, analysis: Analysis) -> list[UserPreference]:
    event = analysis.event

    prefs = (
        db.query(UserPreference)
        .join(User, User.id == UserPreference.user_id)
        .filter(
            User.is_active == True,
            UserPreference.whatsapp_enabled == True,
            UserPreference.whatsapp_phone.isnot(None),
            UserPreference.min_severity <= analysis.severity_score,
        )
        .all()
    )

    recipients: list[UserPreference] = []
    for pref in prefs:
        if pref.topics and event.topic and event.topic not in pref.topics:
            continue
        if pref.regions and event.region and event.region not in pref.regions:
            continue
        recipients.append(pref)
    return recipients


def _ensure_delivery(
    db,
    *,
    alert_id: uuid.UUID,
    channel: DeliveryChannel,
    destination: str,
) -> Delivery | None:
    existing = (
        db.query(Delivery)
        .filter(
            Delivery.alert_id == alert_id,
            Delivery.channel == channel,
            Delivery.destination == destination,
        )
        .first()
    )
    if existing:
        return None

    delivery = Delivery(
        alert_id=alert_id,
        channel=channel,
        status=DeliveryStatus.PENDING,
        destination=destination,
        attempt_count=0,
    )
    db.add(delivery)
    db.flush()
    return delivery


def create_alert_and_deliveries(analysis_id: uuid.UUID, publish_next: bool = True) -> str:
    db = SessionLocal()
    try:
        analysis = (
            db.query(Analysis)
            .options(joinedload(Analysis.event))
            .filter(Analysis.id == analysis_id)
            .first()
        )
        if not analysis:
            print(f"[policy] analysis not found: {analysis_id}")
            return "missing"

        if not should_create_critical_alert(analysis):
            print(
                f"[policy] no alert for analysis={analysis.id} "
                f"(severity={analysis.severity_score}, confidence={analysis.confidence_score})"
            )
            return "no_alert"

        reason = (
            f"CRITICAL policy matched for analysis {analysis.id} "
            f"(severity={analysis.severity_score:.3f}, confidence={analysis.confidence_score:.3f})"
        )

        existing_alert = (
            db.query(Alert)
            .filter(
                Alert.event_id == analysis.event_id,
                Alert.reason == reason,
            )
            .first()
        )
        alert: Alert
        is_new_alert = False
        if existing_alert:
            alert = existing_alert
        else:
            alert = Alert(
                event_id=analysis.event_id,
                alert_level=AlertLevel.CRITICAL,
                reason=reason,
                analysis_snapshot={
                    "analysis_id": str(analysis.id),
                    "severity_score": analysis.severity_score,
                    "confidence_score": analysis.confidence_score,
                    "summary": analysis.summary,
                    "risk_labels": analysis.risk_labels,
                    "topic": analysis.topic,
                    "region": analysis.region,
                },
            )
            db.add(alert)
            db.flush()
            is_new_alert = True

            analysis.event.last_alert_level = AlertLevel.CRITICAL
            analysis.event.last_alert_at = datetime.now(timezone.utc)

        recipients_tg = find_telegram_recipients(db, analysis)
        recipients_wa = find_whatsapp_recipients(db, analysis)
        deliveries: list[Delivery] = []
        for pref in recipients_tg:
            chat_id = (pref.telegram_chat_id or "").strip()
            if not chat_id:
                continue
            delivery = _ensure_delivery(
                db,
                alert_id=alert.id,
                channel=DeliveryChannel.TELEGRAM,
                destination=chat_id,
            )
            if delivery:
                deliveries.append(delivery)

        for pref in recipients_wa:
            phone = (pref.whatsapp_phone or "").strip()
            if not phone:
                continue
            delivery = _ensure_delivery(
                db,
                alert_id=alert.id,
                channel=DeliveryChannel.WHATSAPP,
                destination=phone,
            )
            if delivery:
                deliveries.append(delivery)

        db.commit()

        if publish_next:
            for delivery in deliveries:
                try:
                    payload = {
                        "delivery_id": str(delivery.id),
                        "alert_id": str(alert.id),
                        "destination": delivery.destination,
                    }
                    if delivery.channel == DeliveryChannel.TELEGRAM:
                        publish(DELIVERY_TELEGRAM_QUEUE, payload)
                    elif delivery.channel == DeliveryChannel.WHATSAPP:
                        publish(DELIVERY_WHATSAPP_QUEUE, payload)
                except Exception as exc:
                    print(f"[policy] warning: publish failed for delivery={delivery.id}: {exc}")

        result = "created" if is_new_alert else ("updated" if deliveries else "exists")
        print(
            f"[policy] {result} alert={alert.id} analysis={analysis.id} "
            f"deliveries={len(deliveries)}"
        )
        return result
    except Exception as exc:
        db.rollback()
        print(f"[policy] failed for analysis={analysis_id}: {exc}")
        raise
    finally:
        db.close()


def handle_analysis_result(payload: dict):
    analysis_id = _parse_uuid(payload.get("analysis_id"))
    if not analysis_id:
        print(f"[policy] payload missing analysis_id: {payload}")
        return
    create_alert_and_deliveries(analysis_id, publish_next=True)


def run_consumer():
    print(f"[policy] consuming from {ANALYSIS_RESULT_QUEUE}")
    consumer(ANALYSIS_RESULT_QUEUE, handle_analysis_result)


def run_backfill(limit: int):
    db = SessionLocal()
    try:
        analyses = (
            db.query(Analysis.id)
            .order_by(Analysis.created_at.desc())
            .limit(limit)
            .all()
        )
        analysis_ids = [row[0] for row in analyses]
    finally:
        db.close()

    print(f"[policy] backfill candidates={len(analysis_ids)}")
    result_counts = {"created": 0, "updated": 0, "no_alert": 0, "exists": 0, "missing": 0}
    for analysis_id in analysis_ids:
        result = create_alert_and_deliveries(analysis_id, publish_next=True)
        if result in result_counts:
            result_counts[result] += 1
    print(f"[policy] backfill completed {result_counts}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Policy worker for creating alerts and deliveries.")
    parser.add_argument(
        "--backfill",
        action="store_true",
        help="Evaluate latest analyses from DB instead of consuming queue.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=200,
        help="Maximum number of analyses to process in backfill mode.",
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
