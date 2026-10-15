"""
===============================================================================
KAVACH BIE — Member 2: Integration Adapter for Member 4
Member 4: Conflict and Operational Validation Subsystem
===============================================================================
Exposes predicted delays, scheduled train conflicts, and timetable context
to support Member 4's independent conflict detection and safety certification.

CRITICAL ARCHITECTURAL BOUNDARY:
- Member 2 provides operational delay estimates and timetabled train overlaps.
- Member 2 does NOT certify that a proposed maintenance block is operationally safe.
- Member 4 independently executes signal interlocking checks, traction power (OHE)
  isolation verification, and headway conflict validation.
"""

import logging
from typing import Any, Dict, List, Optional
import pandas as pd

from config import DEFAULT_SAFETY_BUFFER_MINUTES
from predict_delay import get_member4_validation_context
from prediction_schema import Member4ValidationPayload

logger = logging.getLogger("kavach_bie.adapter.member4")


class Member4ValidationAdapter:
    """Adapter for Member 4 (Operational Conflict Validation)."""

    @staticmethod
    def get_validation_payload(
        request: Dict[str, Any],
        train_data: Optional[pd.DataFrame] = None,
        buffer_minutes: int = DEFAULT_SAFETY_BUFFER_MINUTES,
    ) -> Member4ValidationPayload:
        """
        Assemble the standardized Member 4 validation handoff package.
        Returns a validated Member4ValidationPayload Pydantic instance.
        """
        raw_context = get_member4_validation_context(
            request=request,
            train_data=train_data,
            buffer_minutes=buffer_minutes,
        )
        return Member4ValidationPayload(**raw_context)

    @staticmethod
    def extract_conflicting_train_list(
        request: Dict[str, Any],
        train_data: Optional[pd.DataFrame] = None,
    ) -> List[Dict[str, Any]]:
        """Retrieve list of scheduled train services that collide with the window + safety buffer."""
        payload = Member4ValidationAdapter.get_validation_payload(request, train_data=train_data)
        return payload.conflicting_trains
