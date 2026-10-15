"""Firebase Authentication adapter and FastAPI security dependency for KAVACH BIE Member 3."""

import logging
from typing import Any, Dict, Optional

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import settings

logger = logging.getLogger(__name__)
security = HTTPBearer(auto_error=False)

MOCK_USERS: Dict[str, Dict[str, Any]] = {
    "test-token-engineer": {
        "uid": "usr-eng-001",
        "email": "engineer@kavach.railnet.gov.in",
        "role": "MAINTENANCE_ENGINEER",
        "name": "Senior Section Engineer (P-Way)",
    },
    "test-token-admin": {
        "uid": "usr-adm-001",
        "email": "admin@kavach.railnet.gov.in",
        "role": "ADMIN",
        "name": "Chief Operations Manager",
    },
    "test-token-dispatcher": {
        "uid": "usr-disp-001",
        "email": "dispatcher@kavach.railnet.gov.in",
        "role": "DISPATCHER",
        "name": "Section Controller (Operations)",
    },
}


class FirebaseAuthAdapter:
    """Verifies Firebase JWT ID tokens with real Firebase Admin SDK or local test doubles."""

    def __init__(self) -> None:
        self.is_configured = settings.is_firebase_configured and not settings.MOCK_FIREBASE

    def verify_token(self, token: str) -> Dict[str, Any]:
        """Verify token and return user identity and claims."""
        if not token or not token.strip():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Empty or missing authorization token.",
            )

        token = token.strip()

        # If real Firebase is initialized and not in mock mode
        if self.is_configured:
            try:
                from firebase_admin import auth
                decoded_claims = auth.verify_id_token(token)
                return {
                    "uid": decoded_claims.get("uid"),
                    "email": decoded_claims.get("email"),
                    "role": decoded_claims.get("role", "MAINTENANCE_ENGINEER"),
                    "claims": decoded_claims,
                }
            except Exception as exc:
                logger.warning("Firebase ID token verification failed: %s", exc)
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=f"Invalid Firebase ID token: {exc}",
                ) from exc

        # Mock / Test Mode
        if token in MOCK_USERS:
            return MOCK_USERS[token]

        if token.startswith("Bearer "):
            token = token[7:].strip()
            if token in MOCK_USERS:
                return MOCK_USERS[token]

        # In dev mode with auth disabled, allow any test string as username
        if not settings.FIREBASE_AUTH_ENABLED:
            return {
                "uid": f"dev-user-{token[:8]}",
                "email": f"{token[:8]}@kavach.local",
                "role": "MAINTENANCE_ENGINEER",
                "is_dev_fallback": True,
            }

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token unrecognized. Use valid Firebase JWT or 'test-token-engineer'.",
        )


auth_adapter = FirebaseAuthAdapter()


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security),
) -> Dict[str, Any]:
    """FastAPI dependency to extract and verify the authenticated user."""
    if credentials is None:
        if not settings.FIREBASE_AUTH_ENABLED:
            # Anonymous dev fallback
            return {
                "uid": "anonymous-dev-user",
                "email": "dev@kavach.local",
                "role": "MAINTENANCE_ENGINEER",
                "is_anonymous": True,
            }
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header required (Bearer token).",
        )

    return auth_adapter.verify_token(credentials.credentials)
