"""Firebase Cloud Storage repository adapter for KAVACH BIE Member 3."""

import logging
import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.config import settings

logger = logging.getLogger(__name__)


class StorageRepository:
    """Handles dataset file uploads, downloads, and signed URL generation via Firebase Storage."""

    def __init__(self) -> None:
        self.is_configured = settings.is_firebase_configured and not settings.MOCK_FIREBASE
        self._bucket = None

        if self.is_configured:
            try:
                import firebase_admin
                from firebase_admin import credentials, storage

                if not firebase_admin._apps:
                    cred = credentials.Certificate(settings.GOOGLE_APPLICATION_CREDENTIALS)
                    firebase_admin.initialize_app(cred, {
                        "projectId": settings.FIREBASE_PROJECT_ID,
                        "storageBucket": settings.FIREBASE_STORAGE_BUCKET,
                    })
                self._bucket = storage.bucket(settings.FIREBASE_STORAGE_BUCKET)
                logger.info("Connected to Firebase Cloud Storage bucket: %s", settings.FIREBASE_STORAGE_BUCKET)
            except Exception as exc:
                logger.warning("Failed to initialize Firebase Storage bucket: %s. Using local filesystem.", exc)
                self.is_configured = False

    def upload_file(self, local_path: Path, destination_blob_name: str) -> Dict[str, Any]:
        """Upload a file to Firebase Storage or copy to local processed storage."""
        if not local_path.exists():
            raise FileNotFoundError(f"Local file not found: {local_path}")

        file_size = local_path.stat().st_size

        if self.is_configured and self._bucket:
            blob = self._bucket.blob(destination_blob_name)
            blob.upload_from_filename(str(local_path))
            return {
                "destination": destination_blob_name,
                "storage_backend": "FIREBASE_CLOUD_STORAGE",
                "bucket": settings.FIREBASE_STORAGE_BUCKET,
                "size_bytes": file_size,
                "uploaded_at": datetime.now(timezone.utc).isoformat(),
            }

        # Local Filesystem Fallback
        dest_local = settings.DATA_PROCESSED_DIR / Path(destination_blob_name).name
        dest_local.parent.mkdir(parents=True, exist_ok=True)
        if dest_local != local_path:
            shutil.copy2(local_path, dest_local)

        return {
            "destination": str(dest_local),
            "storage_backend": "LOCAL_FILESYSTEM",
            "size_bytes": file_size,
            "uploaded_at": datetime.now(timezone.utc).isoformat(),
        }

    def generate_download_url(self, blob_name: str, expiration_minutes: int = 60) -> str:
        """Generate a signed download URL or local file path."""
        if self.is_configured and self._bucket:
            blob = self._bucket.blob(blob_name)
            return blob.generate_signed_url(
                expiration=timedelta(minutes=expiration_minutes),
                method="GET",
            )
        return f"/api/v1/datasets/download/{Path(blob_name).name}"


storage_repo = StorageRepository()
