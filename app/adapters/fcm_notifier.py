"""Firebase Cloud Messaging (FCM) notification adapter for KAVACH BIE Member 3."""

import logging
from typing import Any, Dict, Optional

from app.config import settings

logger = logging.getLogger(__name__)


class FCMNotificationAdapter:
    """Dispatches push notifications for scheduling and validation lifecycle events."""

    def __init__(self) -> None:
        self.is_configured = settings.is_firebase_configured and not settings.MOCK_FIREBASE
        self.dispatched_notifications: list[Dict[str, Any]] = []

    def send_notification(
        self,
        title: str,
        body: str,
        data: Optional[Dict[str, str]] = None,
        topic: str = "maintenance_dispatch",
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Send FCM message to a topic or specific registration token."""
        msg_payload = {
            "title": title,
            "body": body,
            "data": data or {},
            "target": token if token else f"topic:{topic}",
        }

        if self.is_configured:
            try:
                from firebase_admin import messaging

                notification = messaging.Notification(title=title, body=body)
                if token:
                    message = messaging.Message(notification=notification, data=data or {}, token=token)
                else:
                    message = messaging.Message(notification=notification, data=data or {}, topic=topic)

                response = messaging.send(message)
                logger.info("Dispatched FCM message: %s", response)
                return {"status": "SENT", "message_id": response, "payload": msg_payload}
            except Exception as exc:
                logger.warning("Failed to dispatch live FCM notification: %s", exc)
                return {"status": "FAILED", "error": str(exc), "payload": msg_payload}

        # Test double / mock mode
        self.dispatched_notifications.append(msg_payload)
        logger.info("[MOCK FCM] Dispatched to %s: %s - %s", msg_payload["target"], title, body)
        return {"status": "MOCK_DISPATCHED", "payload": msg_payload}


fcm_notifier = FCMNotificationAdapter()
