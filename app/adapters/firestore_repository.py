"""Cloud Firestore repository adapter for KAVACH BIE Member 3.

Manages persistent application records:
- maintenance_requests/
- optimization_jobs/
- optimization_results/
- validation_results/
- dataset_metadata/
- audit_logs/

Connects to Google Cloud Firestore via Firebase Admin SDK when credentials are configured;
seamlessly falls back to an in-memory mock store for local development and testing.
"""

import logging
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.config import settings

logger = logging.getLogger(__name__)

# Global singleton in-memory mock store for test/dev mode
MOCK_FIRESTORE_STORE: Dict[str, Dict[str, Dict[str, Any]]] = defaultdict(dict)


class FirestoreRepository:
    """Repository handling all Firestore database operations."""

    def __init__(self) -> None:
        self.is_configured = settings.is_firebase_configured and not settings.MOCK_FIREBASE
        self._db = None

        if self.is_configured:
            try:
                import firebase_admin
                from firebase_admin import credentials, firestore

                if not firebase_admin._apps:
                    cred = credentials.Certificate(settings.GOOGLE_APPLICATION_CREDENTIALS)
                    firebase_admin.initialize_app(cred, {
                        "projectId": settings.FIREBASE_PROJECT_ID,
                        "storageBucket": settings.FIREBASE_STORAGE_BUCKET,
                    })
                self._db = firestore.client()
                logger.info("Connected to Google Cloud Firestore project: %s", settings.FIREBASE_PROJECT_ID)
            except Exception as exc:
                logger.warning("Failed to initialize live Cloud Firestore client: %s. Falling back to in-memory store.", exc)
                self.is_configured = False

    # -----------------------------------------------------------------------
    # Maintenance Requests
    # -----------------------------------------------------------------------
    def save_maintenance_request(self, request_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        doc_data = {
            "request_id": request_id,
            **data,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        if self.is_configured and self._db:
            self._db.collection("maintenance_requests").document(request_id).set(doc_data)
        else:
            MOCK_FIRESTORE_STORE["maintenance_requests"][request_id] = doc_data
        return doc_data

    def get_maintenance_request(self, request_id: str) -> Optional[Dict[str, Any]]:
        if self.is_configured and self._db:
            doc = self._db.collection("maintenance_requests").document(request_id).get()
            return doc.to_dict() if doc.exists else None
        return MOCK_FIRESTORE_STORE["maintenance_requests"].get(request_id)

    def list_maintenance_requests(self, limit: int = 50) -> List[Dict[str, Any]]:
        if self.is_configured and self._db:
            docs = self._db.collection("maintenance_requests").limit(limit).stream()
            return [d.to_dict() for d in docs]
        return list(MOCK_FIRESTORE_STORE["maintenance_requests"].values())[:limit]

    # -----------------------------------------------------------------------
    # Optimization Jobs & Results
    # -----------------------------------------------------------------------
    def create_optimization_job(self, job_id: str, request_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        job_data = {
            "job_id": job_id,
            "request_id": request_id,
            "status": "QUEUED",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "payload": payload,
            "result_id": None,
        }
        if self.is_configured and self._db:
            self._db.collection("optimization_jobs").document(job_id).set(job_data)
        else:
            MOCK_FIRESTORE_STORE["optimization_jobs"][job_id] = job_data
        return job_data

    def update_optimization_job(
        self,
        job_id: str,
        status: str,
        details: Optional[Dict[str, Any]] = None,
        result_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        existing = self.get_optimization_job(job_id) or {"job_id": job_id}
        existing.update({
            "status": status,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        })
        if details:
            existing["details"] = details
        if result_id:
            existing["result_id"] = result_id

        if self.is_configured and self._db:
            self._db.collection("optimization_jobs").document(job_id).set(existing, merge=True)
        else:
            MOCK_FIRESTORE_STORE["optimization_jobs"][job_id] = existing
        return existing

    def get_optimization_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        if self.is_configured and self._db:
            doc = self._db.collection("optimization_jobs").document(job_id).get()
            return doc.to_dict() if doc.exists else None
        return MOCK_FIRESTORE_STORE["optimization_jobs"].get(job_id)

    def save_optimization_result(self, job_id: str, result_data: Dict[str, Any]) -> Dict[str, Any]:
        doc_data = {
            "job_id": job_id,
            "saved_at": datetime.now(timezone.utc).isoformat(),
            **result_data,
        }
        if self.is_configured and self._db:
            self._db.collection("optimization_results").document(job_id).set(doc_data)
        else:
            MOCK_FIRESTORE_STORE["optimization_results"][job_id] = doc_data
        return doc_data

    def get_optimization_result(self, job_id: str) -> Optional[Dict[str, Any]]:
        if self.is_configured and self._db:
            doc = self._db.collection("optimization_results").document(job_id).get()
            return doc.to_dict() if doc.exists else None
        return MOCK_FIRESTORE_STORE["optimization_results"].get(job_id)

    # -----------------------------------------------------------------------
    # Operational Validation Outcomes
    # -----------------------------------------------------------------------
    def save_validation_result(self, validation_id: str, val_data: Dict[str, Any]) -> Dict[str, Any]:
        doc_data = {
            "validation_id": validation_id,
            "recorded_at": datetime.now(timezone.utc).isoformat(),
            **val_data,
        }
        if self.is_configured and self._db:
            self._db.collection("validation_results").document(validation_id).set(doc_data)
        else:
            MOCK_FIRESTORE_STORE["validation_results"][validation_id] = doc_data
        return doc_data

    # -----------------------------------------------------------------------
    # Dataset Metadata & Provenance
    # -----------------------------------------------------------------------
    def save_dataset_metadata(self, dataset_id: str, meta: Dict[str, Any]) -> Dict[str, Any]:
        doc_data = {
            "dataset_id": dataset_id,
            "synced_at": datetime.now(timezone.utc).isoformat(),
            **meta,
        }
        if self.is_configured and self._db:
            self._db.collection("dataset_metadata").document(dataset_id).set(doc_data)
        else:
            MOCK_FIRESTORE_STORE["dataset_metadata"][dataset_id] = doc_data
        return doc_data

    def list_dataset_metadata(self) -> List[Dict[str, Any]]:
        if self.is_configured and self._db:
            docs = self._db.collection("dataset_metadata").stream()
            return [d.to_dict() for d in docs]
        return list(MOCK_FIRESTORE_STORE["dataset_metadata"].values())

    # -----------------------------------------------------------------------
    # Audit Logs
    # -----------------------------------------------------------------------
    def log_audit_event(self, user_id: str, action: str, details: Dict[str, Any]) -> Dict[str, Any]:
        event_id = f"aud_{int(datetime.now(timezone.utc).timestamp() * 1000)}"
        event_data = {
            "event_id": event_id,
            "user_id": user_id,
            "action": action,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "details": details,
        }
        if self.is_configured and self._db:
            self._db.collection("audit_logs").document(event_id).set(event_data)
        else:
            MOCK_FIRESTORE_STORE["audit_logs"][event_id] = event_data
        return event_data


firestore_repo = FirestoreRepository()
