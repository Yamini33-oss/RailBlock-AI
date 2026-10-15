"""
===============================================================================
KAVACH BIE — Member 2 Team Integration Adapters Package
===============================================================================
Exports adapters and mock implementations for cross-module integration:
- Member1DataAdapter: Data ingestion, schema harmonization, quality audits
- Member3OptimizationAdapter: Optimization candidate ranking and Pareto tradeoffs
- Member4ValidationAdapter: Operational conflict and interlocking validation handoff
- Member5DashboardAdapter: Mountable FastAPI APIRouter and dashboard services
- MockMember1, MockMember3, MockMember4, MockMember5: Offline testing simulations
"""

from adapters.member1_adapter import Member1DataAdapter
from adapters.member3_adapter import Member3OptimizationAdapter
from adapters.member4_adapter import Member4ValidationAdapter
from adapters.member5_adapter import get_member5_router
from adapters.mocks import (
    MockMember1DataIngestion,
    MockMember3OptimizationEngine,
    MockMember4SafetyValidation,
    MockMember5WebDashboard,
)

__all__ = [
    "Member1DataAdapter",
    "Member3OptimizationAdapter",
    "Member4ValidationAdapter",
    "get_member5_router",
    "MockMember1DataIngestion",
    "MockMember3OptimizationEngine",
    "MockMember4SafetyValidation",
    "MockMember5WebDashboard",
]
