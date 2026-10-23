"""
ResourceShift AI - FastAPI Application
---------------------------------------
Provides REST API endpoints for multi-resource telemetry ingestion/querying,
deterministic anomaly access, and Human-in-the-Loop (HITL) action approvals.

Endpoints:
- GET  /api/health            Application status & capability metadata (no secrets).
- GET  /api/telemetry         Multi-resource telemetry readings with filters.
- GET  /api/anomalies         Detected baseline anomalies across resources.
- POST /api/actions/approve   Record human operator approval of a proposed action.
- POST /api/actions/reject    Record human operator rejection with reason.
"""

from __future__ import annotations

import datetime
from typing import Any, Dict, List, Optional
from fastapi import FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from backend.app.core.audit import record_action_decision, get_audit_trail, list_proposals
from backend.app.core.telemetry_store import store
from backend.app.core.analysis import RESOURCE_CONFIGS
from backend.app.agent.investigator import GeminiInvestigator, InvestigationResult

app = FastAPI(
    title="ResourceShift AI API",
    description="Campus Multi-Resource Optimization & Waste Mitigation Platform",
    version="0.2.0",
)

# Configure CORS to explicitly allow deployed Vercel frontend, preview domains, and local dev
import os

ALLOWED_ORIGINS = [
    "https://hackathon-2026-umber.vercel.app",
    "http://localhost:5173",
    "http://localhost:3000",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:3000",
]

env_origins = os.getenv("CORS_ORIGINS", "")
if env_origins:
    ALLOWED_ORIGINS.extend([origin.strip() for origin in env_origins.split(",") if origin.strip()])

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==============================================================================
# Pydantic Schemas
# ==============================================================================

class HealthResponse(BaseModel):
    status: str
    service: str
    version: str
    resources_supported: List[str]
    capabilities: Dict[str, Any]
    timestamp: str


class TelemetryItem(BaseModel):
    timestamp: str
    building_id: str
    resource_type: str
    consumption: float
    unit: str
    occupancy: int
    scheduled_open: bool
    equipment_type: str
    equipment_notes: str


class TelemetryResponse(BaseModel):
    total: int
    limit: int
    offset: int
    readings: List[TelemetryItem]


class AnomalyItem(BaseModel):
    anomaly_id: str
    reading_index: int
    resource_type: str
    unit: str
    timestamp: str
    building_id: str
    actual_usage: float
    expected_usage: float
    excess_consumption: float
    severity: str
    supporting_evidence: Dict[str, Any]


class AnomaliesResponse(BaseModel):
    total_anomalies: int
    limit: int
    anomalies: List[AnomalyItem]


class ApproveActionRequest(BaseModel):
    proposal_id: str = Field(..., min_length=1, description="Identifier of the proposal being approved.")
    approved_by: str = Field(..., min_length=1, description="Username or ID of the facility manager.")
    notes: Optional[str] = Field("", description="Optional operator notes or work ticket reference.")


class RejectActionRequest(BaseModel):
    proposal_id: str = Field(..., min_length=1, description="Identifier of the proposal being rejected.")
    rejected_by: str = Field(..., min_length=1, description="Username or ID of the facility manager.")
    reason: Optional[str] = Field("", description="Optional reason for rejecting the proposal.")


class ActionDecisionResponse(BaseModel):
    status: str
    proposal_id: str
    audit_id: str
    recorded_at: str
    decision: str
    actor: str
    notes_or_reason: str
    no_actuation_guarantee: bool


class InvestigateRequest(BaseModel):
    anomaly_id: str = Field(..., min_length=1, description="Identifier of the anomaly to investigate.")
    context_notes: Optional[str] = Field("", description="Optional operator notes or context.")


# ==============================================================================
# Endpoints
# ==============================================================================

@app.get("/api/health", response_model=HealthResponse, tags=["Health"])
def get_health() -> HealthResponse:
    """Returns application health and implementation status without exposing secrets."""
    return HealthResponse(
        status="healthy",
        service="ResourceShift AI",
        version="0.2.0",
        resources_supported=list(RESOURCE_CONFIGS.keys()),
        capabilities={
            "synthetic_telemetry": True,
            "deterministic_detection": True,
            "savings_estimation": True,
            "hitl_approval_pipeline": True,
            "mcp_server": True,
            "gemini_reasoning": "planned",
            "firestore_persistence": "planned",
        },
        timestamp=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    )


@app.get("/api/telemetry", response_model=TelemetryResponse, tags=["Telemetry"])
def get_telemetry(
    resource_type: Optional[str] = Query(None, description="Filter: 'electricity', 'water', or 'fuel'"),
    building_id: Optional[str] = Query(None, description="Filter: e.g. 'ENG_HALL_01'"),
    start_time: Optional[str] = Query(None, description="ISO-8601 start timestamp filter"),
    end_time: Optional[str] = Query(None, description="ISO-8601 end timestamp filter"),
    limit: int = Query(100, ge=1, le=1000, description="Page limit"),
    offset: int = Query(0, ge=0, description="Page offset"),
) -> TelemetryResponse:
    """Retrieves multi-resource telemetry readings with optional filters and pagination."""
    if resource_type:
        r_type = resource_type.lower().strip()
        if r_type not in RESOURCE_CONFIGS:
            raise HTTPException(
                status_code=422,
                detail=f"Invalid resource_type '{resource_type}'. Allowed: {list(RESOURCE_CONFIGS.keys())}",
            )
    else:
        r_type = None

    result = store.get_telemetry(
        resource_type=r_type,
        building_id=building_id.strip() if building_id else None,
        start_time=start_time.strip() if start_time else None,
        end_time=end_time.strip() if end_time else None,
        limit=limit,
        offset=offset,
    )
    return TelemetryResponse(**result)


@app.get("/api/anomalies", response_model=AnomaliesResponse, tags=["Anomalies"])
def get_anomalies(
    resource_type: Optional[str] = Query(None, description="Filter by resource ('electricity', 'water', 'fuel')"),
    severity: Optional[str] = Query(None, description="Filter by severity ('low', 'medium', 'high', 'critical')"),
    building_id: Optional[str] = Query(None, description="Filter by building ID"),
    limit: int = Query(50, ge=1, le=500, description="Max anomalies to return"),
) -> AnomaliesResponse:
    """Retrieves detected baseline anomalies across resources."""
    if resource_type:
        r_type = resource_type.lower().strip()
        if r_type not in RESOURCE_CONFIGS:
            raise HTTPException(
                status_code=422,
                detail=f"Invalid resource_type '{resource_type}'. Allowed: {list(RESOURCE_CONFIGS.keys())}",
            )
    else:
        r_type = None

    if severity:
        sev = severity.lower().strip()
        if sev not in ("low", "medium", "high", "critical"):
            raise HTTPException(
                status_code=422,
                detail=f"Invalid severity '{severity}'. Allowed: ['low', 'medium', 'high', 'critical']",
            )
    else:
        sev = None

    result = store.get_anomalies(
        resource_type=r_type,
        severity=sev,
        building_id=building_id.strip() if building_id else None,
        limit=limit,
    )
    return AnomaliesResponse(**result)


@app.post("/api/actions/approve", response_model=ActionDecisionResponse, tags=["Actions"])
def approve_action(payload: ApproveActionRequest) -> ActionDecisionResponse:
    """
    Records a human facility manager's approval of a proposed shift recommendation.
    Enforces the Human-in-the-Loop invariant: creates an audit trail entry for manual
    operational follow-up; never triggers automated physical equipment control.
    """
    try:
        audit_entry = record_action_decision(
            proposal_id=payload.proposal_id.strip(),
            decision="approved",
            actor=payload.approved_by.strip(),
            notes_or_reason=payload.notes or "",
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return ActionDecisionResponse(
        status="approved",
        proposal_id=payload.proposal_id,
        audit_id=audit_entry["audit_id"],
        recorded_at=audit_entry["timestamp"],
        decision=audit_entry["decision"],
        actor=audit_entry["actor"],
        notes_or_reason=audit_entry["notes_or_reason"],
        no_actuation_guarantee=audit_entry["no_actuation_guarantee"],
    )


@app.post("/api/actions/reject", response_model=ActionDecisionResponse, tags=["Actions"])
def reject_action(payload: RejectActionRequest) -> ActionDecisionResponse:
    """
    Records a human facility manager's rejection of a proposed recommendation along with an optional reason.
    """
    try:
        audit_entry = record_action_decision(
            proposal_id=payload.proposal_id.strip(),
            decision="rejected",
            actor=payload.rejected_by.strip(),
            notes_or_reason=payload.reason or "",
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return ActionDecisionResponse(
        status="rejected",
        proposal_id=payload.proposal_id,
        audit_id=audit_entry["audit_id"],
        recorded_at=audit_entry["timestamp"],
        decision=audit_entry["decision"],
        actor=audit_entry["actor"],
        notes_or_reason=audit_entry["notes_or_reason"],
        no_actuation_guarantee=audit_entry["no_actuation_guarantee"],
    )


@app.get("/api/audit", tags=["Actions"])
def get_audit() -> Dict[str, Any]:
    """Returns the immutable audit log and registered proposals."""
    return {
        "audit_trail": get_audit_trail(),
        "proposals": list_proposals(),
    }


@app.post("/api/investigate", response_model=InvestigationResult, tags=["Investigation"])
async def investigate_anomaly(payload: InvestigateRequest) -> InvestigationResult:
    """
    Triggers an autonomous root-cause investigation for a detected resource anomaly.
    Uses Google Gemini with FastMCP diagnostic tools to analyze schedule, sensor logs,
    and equipment ratings, then automatically registers an advisory proposal for human review.
    """
    try:
        investigator = GeminiInvestigator()
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc

    try:
        result = await investigator.investigate(
            anomaly_id=payload.anomaly_id,
            context_notes=payload.context_notes or "",
        )
        return result
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Investigation workflow failed: {exc}",
        ) from exc
