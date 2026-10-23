"""
ResourceShift AI - Model Context Protocol (MCP) Server
-------------------------------------------------------
Exposes standardized analytical and investigative tools for the Gemini reasoning agent.

Supported Tools:
1. get_anomaly            - Retrieve detailed evidence for a detected anomaly.
2. check_schedule          - Check academic building and subsystem schedules.
3. check_equipment         - Retrieve equipment specifications and operating constraints.
4. get_resource_history    - Retrieve historical telemetry for electricity, water, or fuel.
5. estimate_savings        - Deterministically calculate resource, cost, and carbon savings.
6. create_proposal         - Register a shift recommendation for human facility manager review.

Security & Safety Guarantees:
- Strictly READ-ONLY for all diagnostic and investigation tools.
- 'create_proposal' records proposals into the audit database; it DOES NOT execute them.
- NO tools exist to actuate physical relays, adjust valves, toggle equipment, or modify hardware.
- Equipment notes and free-text inputs are sanitized and never evaluated as instructions.
"""

from __future__ import annotations

import datetime
from typing import Any, Dict, List, Optional

try:
    from mcp.server.fastmcp import FastMCP
except (ImportError, ModuleNotFoundError):
    from mcp.server.mcpserver import MCPServer as FastMCP

from backend.app.core.telemetry_store import store
from backend.app.core.audit import save_proposal
from backend.app.core.analysis import (
    estimate_savings as core_estimate_savings,
    RESOURCE_CONFIGS,
)

# Canonical equipment inventory for ENG_HALL_01
EQUIPMENT_REGISTRY: Dict[str, Dict[str, Any]] = {
    "AHU-3": {
        "equipment_id": "AHU-3",
        "name": "Floor 3 Air Handling Unit Chiller",
        "building_id": "ENG_HALL_01",
        "subsystem": "HVAC",
        "rated_capacity": "45 kW",
        "normal_operating_hours": "07:00 - 20:00 Weekdays",
        "unoccupied_policy": "Setback cooling to 74F / heating to 62F between 20:00 and 07:00",
        "criticality": "high",
    },
    "VACUUM_FURNACE": {
        "equipment_id": "VACUUM_FURNACE",
        "name": "Robotics & Materials Lab Vacuum Heat-Treatment Furnace",
        "building_id": "ENG_HALL_01",
        "subsystem": "LAB_EQUIPMENT",
        "rated_capacity": "60 kW",
        "normal_operating_hours": "Attended hours only (09:00 - 18:00)",
        "unoccupied_policy": "De-energized standby; overnight bake cycles require authorized permit",
        "criticality": "high",
    },
    "AUDITORIUM_201_LIGHTS": {
        "equipment_id": "AUDITORIUM_201_LIGHTS",
        "name": "Auditorium 201 Theatrical & Bank Lighting",
        "building_id": "ENG_HALL_01",
        "subsystem": "LIGHTING",
        "rated_capacity": "35 kW",
        "normal_operating_hours": "08:00 - 20:00 Weekdays",
        "unoccupied_policy": "Automatic curfew shutdown at 20:30; emergency egress path lights only",
        "criticality": "medium",
    },
    "COOLING_TOWER_PUMP": {
        "equipment_id": "COOLING_TOWER_PUMP",
        "name": "Cooling Tower Auxiliary Condensation Circulation Pump",
        "building_id": "ENG_HALL_01",
        "subsystem": "HVAC",
        "rated_capacity": "30 kW",
        "normal_operating_hours": "On-demand chiller heat rejection",
        "unoccupied_policy": "Interlocked with active chiller load; pump must shut down when chillers idle",
        "criticality": "high",
    },
    "HPC_CLUSTER": {
        "equipment_id": "HPC_CLUSTER",
        "name": "Research Multi-Node GPU Compute Cluster",
        "building_id": "ENG_HALL_01",
        "subsystem": "LAB_EQUIPMENT",
        "rated_capacity": "50 kW",
        "normal_operating_hours": "Continuous 24/7 compute with power-capping",
        "unoccupied_policy": "Dynamic frequency scaling eco-governor required 21:00 - 06:00 unless prioritized",
        "criticality": "medium",
    },
    "COMPRESSOR_FL4": {
        "equipment_id": "COMPRESSOR_FL4",
        "name": "Floor 4 Pneumatic Damper Actuator Air Compressor",
        "building_id": "ENG_HALL_01",
        "subsystem": "HVAC",
        "rated_capacity": "15 kW",
        "normal_operating_hours": "Intermittent duty (< 20% duty cycle)",
        "unoccupied_policy": "Duty cycle > 50% overnight indicates pneumatic tubing leak",
        "criticality": "medium",
    },
    "FLUSHOMETER_FL2": {
        "equipment_id": "FLUSHOMETER_FL2",
        "name": "Floor 2 Restroom Restroom Flushometer Battery",
        "building_id": "ENG_HALL_01",
        "subsystem": "PLUMBING_FIXTURE",
        "rated_capacity": "Water pressure 60 PSI",
        "normal_operating_hours": "Occupancy driven",
        "unoccupied_policy": "Continuous flow overnight indicates diaphragm failure",
        "criticality": "medium",
    },
    "IRRIGATION_ZONE_4": {
        "equipment_id": "IRRIGATION_ZONE_4",
        "name": "North Quad Landscaping Irrigation Zone 4",
        "building_id": "ENG_HALL_01",
        "subsystem": "IRRIGATION",
        "rated_capacity": "550 L/hr",
        "normal_operating_hours": "05:00 - 05:30 Tuesday/Thursday",
        "unoccupied_policy": "Solenoid must be closed at all other times",
        "criticality": "low",
    },
    "BOILER_BURNER_2": {
        "equipment_id": "BOILER_BURNER_2",
        "name": "Hydronic Heating Boiler Burner 2",
        "building_id": "ENG_HALL_01",
        "subsystem": "HEATING_BOILER",
        "rated_capacity": "45 L/hr fuel oil",
        "normal_operating_hours": "Winter heating only; morning warmup 05:00-08:00 in autumn",
        "unoccupied_policy": "Burner 2 should be in warm standby (0 L/hr) during mild autumn nights",
        "criticality": "high",
    },
}


def create_mcp_server(name: str = "ResourceShift-MCP-Server") -> FastMCP:
    """Creates and configures the FastMCP server with all investigation tools."""
    server = FastMCP(name)

    # --------------------------------------------------------------------------
    # Tool 1: get_anomaly
    # --------------------------------------------------------------------------
    @server.tool()
    def get_anomaly(anomaly_id: str) -> Dict[str, Any]:
        """
        Retrieves detailed deterministic evidence for a detected anomaly.

        Args:
            anomaly_id: Identifier of the anomaly (e.g. 'ANOM-ELEC-20261004T210').

        Returns:
            Structured dictionary with anomaly metrics, timestamp, and supporting evidence.
        """
        if not anomaly_id or not anomaly_id.strip():
            return {"status": "error", "message": "anomaly_id cannot be empty."}

        target_id = anomaly_id.strip()
        anomaly = store.get_anomaly_by_id(target_id)
        if not anomaly:
            # Try fuzzy search if prefix or partial match
            all_anoms = store.get_anomalies(limit=500)["anomalies"]
            for a in all_anoms:
                if target_id.lower() in a["anomaly_id"].lower():
                    anomaly = a
                    break

        if not anomaly:
            return {
                "status": "not_found",
                "anomaly_id": target_id,
                "message": f"Anomaly with ID '{target_id}' was not found in active detected anomalies.",
            }

        return {
            "status": "success",
            "anomaly": anomaly,
        }

    # --------------------------------------------------------------------------
    # Tool 2: check_schedule
    # --------------------------------------------------------------------------
    @server.tool()
    def check_schedule(
        building_id: str = "ENG_HALL_01",
        timestamp: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Checks whether the building or equipment is scheduled to be open/operating
        at a given timestamp.

        Args:
            building_id: Unique building ID (default 'ENG_HALL_01').
            timestamp: ISO-8601 timestamp string (e.g. '2026-10-04T22:00:00').
                       If omitted, defaults to current UTC time.

        Returns:
            Schedule evaluation including scheduled_open boolean, regular hours,
            and any registered evening classes or events.
        """
        if not building_id or not building_id.strip():
            return {"status": "error", "message": "building_id cannot be empty."}

        try:
            if timestamp and timestamp.strip():
                dt = datetime.datetime.fromisoformat(timestamp.strip())
            else:
                dt = datetime.datetime.now(datetime.timezone.utc)
        except Exception as exc:
            return {"status": "error", "message": f"Invalid ISO timestamp format: {exc}"}

        hour = dt.hour
        is_weekend = dt.weekday() >= 5
        weekday_name = dt.strftime("%A")

        # Academic schedule: Monday-Friday 07:00 to 20:00
        is_open = (not is_weekend) and (7 <= hour < 20)

        # Realistic academic calendar context
        events = []
        if is_open:
            events.append("Standard Undergraduate Lectures & Laboratories in session")
        elif not is_weekend and (18 <= hour < 20):
            events.append("Graduate Seminar (Room 104)")
        elif is_weekend and (10 <= hour < 16):
            events.append("Unscheduled student study group access (Lobby only)")

        return {
            "status": "success",
            "building_id": building_id.strip(),
            "timestamp": dt.isoformat(),
            "day_of_week": weekday_name,
            "hour_of_day": hour,
            "is_weekend": is_weekend,
            "scheduled_open": is_open,
            "operating_hours": "07:00 - 20:00 Monday through Friday; Closed Weekends",
            "is_after_hours": not is_open,
            "registered_events": events,
        }

    # --------------------------------------------------------------------------
    # Tool 3: check_equipment
    # --------------------------------------------------------------------------
    @server.tool()
    def check_equipment(
        equipment_id: str,
        building_id: str = "ENG_HALL_01",
    ) -> Dict[str, Any]:
        """
        Retrieves operating specifications, rated load, and after-hours policies
        for specific building equipment.

        Args:
            equipment_id: Equipment identifier (e.g. 'AHU-3', 'VACUUM_FURNACE', 'BOILER_BURNER_2').
            building_id: Facility identifier (default 'ENG_HALL_01').

        Returns:
            Equipment specifications, rated capacities, and after-hours policy guidelines.
        """
        if not equipment_id or not equipment_id.strip():
            return {"status": "error", "message": "equipment_id cannot be empty."}

        eq_key = equipment_id.strip().upper()
        if eq_key in EQUIPMENT_REGISTRY:
            return {
                "status": "success",
                "equipment": EQUIPMENT_REGISTRY[eq_key],
            }

        # Fuzzy lookup
        for key, details in EQUIPMENT_REGISTRY.items():
            if eq_key in key or key in eq_key:
                return {
                    "status": "success",
                    "equipment": details,
                }

        return {
            "status": "unindexed_equipment",
            "equipment_id": equipment_id,
            "building_id": building_id,
            "message": f"Equipment '{equipment_id}' is not indexed in standard building BMS registry.",
            "general_policy": "All non-emergency equipment must be powered down or placed into eco-setback during closed hours (20:00 - 07:00).",
        }

    # --------------------------------------------------------------------------
    # Tool 4: get_resource_history
    # --------------------------------------------------------------------------
    @server.tool()
    def get_resource_history(
        resource_type: str,
        hours: int = 24,
        building_id: str = "ENG_HALL_01",
    ) -> Dict[str, Any]:
        """
        Retrieves historical telemetry readings for electricity, water, or fuel.

        Args:
            resource_type: 'electricity', 'water', or 'fuel'.
            hours: Number of past hourly intervals to return (1 to 168).
            building_id: Building identifier.

        Returns:
            List of telemetry readings sorted chronologically.
        """
        r_type = resource_type.lower().strip()
        if r_type not in RESOURCE_CONFIGS:
            return {
                "status": "error",
                "message": f"Invalid resource_type '{resource_type}'. Allowed: {list(RESOURCE_CONFIGS.keys())}",
            }

        if hours < 1 or hours > 168:
            return {
                "status": "error",
                "message": f"hours must be between 1 and 168 (got {hours}).",
            }

        telem = store.get_telemetry(
            resource_type=r_type,
            building_id=building_id.strip() if building_id else None,
            limit=hours,
            offset=0,
        )

        return {
            "status": "success",
            "resource_type": r_type,
            "unit": RESOURCE_CONFIGS[r_type]["unit"],
            "count": len(telem["readings"]),
            "readings": telem["readings"],
        }

    # --------------------------------------------------------------------------
    # Tool 5: estimate_savings
    # --------------------------------------------------------------------------
    @server.tool()
    def estimate_savings(
        resource_type: str,
        excess_amount: float,
        duration_hours: float = 1.0,
        tariff_rate: Optional[float] = None,
        co2_factor: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Deterministically calculates estimated resource, cost, and environmental savings
        for a potential intervention.

        Args:
            resource_type: 'electricity', 'water', or 'fuel'.
            excess_amount: Excess consumption rate per hour (in kWh or Litres).
            duration_hours: Duration of the waste period in hours (default 1.0).
            tariff_rate: Optional cost per unit in USD override.
            co2_factor: Optional carbon emission factor per unit override.

        Returns:
            Deterministic savings projections with disclaimers.
        """
        r_type = resource_type.lower().strip()
        if r_type not in RESOURCE_CONFIGS:
            return {
                "status": "error",
                "message": f"Invalid resource_type '{resource_type}'. Allowed: {list(RESOURCE_CONFIGS.keys())}",
            }

        if excess_amount < 0:
            return {"status": "error", "message": f"excess_amount cannot be negative, got {excess_amount}."}
        if duration_hours <= 0:
            return {"status": "error", "message": f"duration_hours must be positive, got {duration_hours}."}

        total_excess = float(excess_amount) * float(duration_hours)

        try:
            savings = core_estimate_savings(
                actual_kwh=total_excess,
                baseline_kwh=0.0,
                tariff_rate=tariff_rate,
                co2_factor=co2_factor,
                resource_type=r_type,
            )
            return {
                "status": "success",
                "duration_hours": duration_hours,
                "savings": savings,
            }
        except ValueError as exc:
            return {"status": "error", "message": str(exc)}

    # --------------------------------------------------------------------------
    # Tool 6: create_proposal
    # --------------------------------------------------------------------------
    @server.tool()
    def create_proposal(
        anomaly_id: str,
        resource_type: str,
        recommended_action: str,
        reason: str,
        estimated_savings_usd: float,
        estimated_co2_kg: float,
        confidence_score: float = 0.90,
    ) -> Dict[str, Any]:
        """
        Registers an optimization recommendation for human facility manager review.

        SAFETY INVARIANT:
        This tool records the proposal in the pending review queue. It DOES NOT
        execute or control physical equipment. Approval by a human operator is required.

        Args:
            anomaly_id: Associated anomaly identifier.
            resource_type: 'electricity', 'water', or 'fuel'.
            recommended_action: Actionable recommendation (e.g. 'Set Floor 3 HVAC to setback mode').
            reason: Root-cause explanation backed by schedule/sensor evidence.
            estimated_savings_usd: Projected cost reduction in USD.
            estimated_co2_kg: Projected carbon emissions avoided in kg CO2.
            confidence_score: AI confidence metric between 0.0 and 1.0.

        Returns:
            Created proposal record in 'pending_review' status.
        """
        if not anomaly_id or not anomaly_id.strip():
            return {"status": "error", "message": "anomaly_id cannot be empty."}
        if not recommended_action or not recommended_action.strip():
            return {"status": "error", "message": "recommended_action cannot be empty."}
        if not reason or not reason.strip():
            return {"status": "error", "message": "reason cannot be empty."}

        r_type = resource_type.lower().strip()
        if r_type not in RESOURCE_CONFIGS:
            return {
                "status": "error",
                "message": f"Invalid resource_type '{resource_type}'. Allowed: {list(RESOURCE_CONFIGS.keys())}",
            }

        proposal_record = save_proposal({
            "anomaly_id": anomaly_id.strip(),
            "resource_type": r_type,
            "recommended_action": recommended_action.strip(),
            "reason": reason.strip(),
            "estimated_savings_usd": max(0.0, float(estimated_savings_usd)),
            "estimated_co2_kg": max(0.0, float(estimated_co2_kg)),
            "confidence_score": min(1.0, max(0.0, float(confidence_score))),
        })

        return {
            "status": "proposal_created",
            "proposal": proposal_record,
            "message": "Proposal successfully recorded for human facility manager review. No physical equipment was actuated.",
        }

    return server
